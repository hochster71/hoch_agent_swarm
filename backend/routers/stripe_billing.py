"""Stripe billing router — catalog + checkout (test-mode by default).

Endpoints (prefix /api/stripe):
  GET  /catalog   public pricing (no price ids, no secrets) + mode banner
  GET  /mode      effective billing mode for ops/widget
  POST /checkout  create a Checkout Session for a catalog tier

Fail-closed design:
  * A checkout is refused unless mode.can_charge() is true.
  * If a live key is present but the founder switch is OFF (test_locked), we
    return 409 with a clear message — we never silently create a live session.
  * The Stripe price id is resolved for the EFFECTIVE mode only; a test run can
    never reach a live price id and vice-versa.
  * tier_id is echoed into session metadata so the webhook can map payment ->
    entitlement without trusting client input twice.

Refs:
  Checkout Sessions      https://docs.stripe.com/api/checkout/sessions/create
  Subscriptions vs one-time (mode)  https://docs.stripe.com/payments/checkout
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import stripe
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.billing import catalog as catalog_mod
from backend.billing import mode as billing_mode

logger = logging.getLogger("stripe_billing")
router = APIRouter(prefix="/api/stripe", tags=["stripe-billing"])


def _configure_stripe() -> None:
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "").strip()


class CheckoutRequest(BaseModel):
    tier_id: str
    success_url: str = "https://example.com/billing/success?session_id={CHECKOUT_SESSION_ID}"
    cancel_url: str = "https://example.com/billing/cancel"
    customer_email: Optional[str] = None


@router.get("/catalog")
def get_catalog() -> dict:
    return catalog_mod.public_catalog()


@router.get("/mode")
def get_mode() -> dict:
    return billing_mode.status()


@router.post("/checkout")
def create_checkout(req: CheckoutRequest) -> dict:
    m = billing_mode.effective_mode()
    if m == billing_mode.MODE_DISABLED:
        raise HTTPException(status_code=503, detail="Billing disabled: no Stripe key configured.")
    if m == billing_mode.MODE_TEST_LOCKED:
        raise HTTPException(
            status_code=409,
            detail="Live key detected but founder switch is OFF. Set HASF_BILLING_LIVE=1 to go live.",
        )

    tier = catalog_mod.get_tier(req.tier_id)
    if not tier:
        raise HTTPException(status_code=404, detail=f"Unknown tier: {req.tier_id}")
    if tier["kind"] == "freemium":
        raise HTTPException(status_code=400, detail="Free tier requires no checkout.")

    price_id = catalog_mod.resolve_price_id(tier)
    if not price_id or str(price_id).startswith("REPLACE_"):
        raise HTTPException(
            status_code=409,
            detail=(
                f"Tier '{req.tier_id}' has no Stripe price id for {m} mode yet. "
                "Create the price in Stripe and set it in pricing_catalog.json "
                "(see docs/billing/GO_LIVE_CHECKLIST.md, step 2)."
            ),
        )

    checkout_mode = tier.get("checkout_mode")  # 'subscription' | 'payment'
    _configure_stripe()
    try:
        session = stripe.checkout.Session.create(
            mode=checkout_mode,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=req.success_url,
            cancel_url=req.cancel_url,
            customer_email=req.customer_email,
            metadata={"tier_id": req.tier_id, "tier": tier["entitlement"]["tier"]},
        )
    except stripe.StripeError as exc:  # pragma: no cover - network path
        logger.warning("Stripe checkout error: %s", exc)
        raise HTTPException(status_code=502, detail=f"Stripe error: {exc.user_message or 'checkout failed'}")

    return {
        "session_id": session["id"],
        "url": session["url"],
        "mode": checkout_mode,
        "billing_mode": m,
        "tier_id": req.tier_id,
    }
