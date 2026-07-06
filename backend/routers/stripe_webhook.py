"""Stripe webhook router.

Endpoint: POST /api/stripe/webhook
Tunnel:   https://portfolio-hoch-agent-swarm.ngrok-free.dev/api/stripe/webhook

Security design:
1. Raw bytes only — request.body() before any parsing.
   Stripe HMAC-SHA256 covers raw payload; JSON pre-parse invalidates signature.
   Ref: https://docs.stripe.com/webhooks#verify-official-libraries
2. Fail-closed secret — missing/malformed STRIPE_WEBHOOK_SECRET returns 500.
3. Idempotency guard — seen event IDs tracked in memory.
   Ref: https://docs.stripe.com/webhooks#handle-duplicate-events
4. Always 2xx for unhandled types — avoids Stripe 72-hour retry storms.
   Ref: https://docs.stripe.com/webhooks#best-practices

Events (minimum viable SaaS set — HASF Epic Fury 2026):
  checkout.session.completed    initial payment / subscription created
  invoice.paid                  renewal (fires every billing cycle)
  invoice.payment_failed        payment failed — notify customer
  customer.subscription.updated plan change
  customer.subscription.deleted cancellation — revoke access

Refs:
  [1] https://docs.stripe.com/webhooks
  [2] https://docs.stripe.com/billing/subscriptions/webhooks
  [3] https://docs.stripe.com/payments/checkout/build-subscriptions
"""
from __future__ import annotations

import logging
import os
from typing import Any, Set

import stripe
from fastapi import APIRouter, HTTPException, Request, Response

from backend.billing import entitlements

logger = logging.getLogger("stripe_webhook")
router = APIRouter(prefix="/api/stripe", tags=["stripe"])
_seen_event_ids: Set[str] = set()


def _f(obj: Any, key: str, default: Any = None) -> Any:
    """Field accessor safe for both plain dicts and Stripe SDK StripeObjects.

    stripe>=5 returns typed StripeObject instances that support obj[key] and
    `key in obj` but NOT .get() — this helper normalises access.
    """
    try:
        return obj[key]
    except (KeyError, TypeError, IndexError):
        return default


def _webhook_secret() -> str:
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
    if not secret.startswith("whsec_"):
        raise HTTPException(
            status_code=500,
            detail="STRIPE_WEBHOOK_SECRET missing or invalid. Set whsec_... in .env.",
        )
    return secret


@router.post("/webhook", status_code=200)
async def stripe_webhook(request: Request) -> Response:
    """Verify Stripe signature and dispatch event.

    Uses request.body() (raw bytes) — never request.json().
    Stripe signature covers raw payload; pre-parsing breaks verification.
    https://docs.stripe.com/webhooks#verify-official-libraries
    """
    payload: bytes = await request.body()
    sig_header: str = request.headers.get("stripe-signature", "")

    if not sig_header:
        logger.warning("Webhook missing Stripe-Signature header — rejected.")
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header.")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=_webhook_secret(),
        )
    except stripe.SignatureVerificationError as exc:
        logger.warning("Signature verification failed: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid Stripe signature.")
    except ValueError as exc:
        logger.warning("Payload parse error: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid payload.")

    event_id: str = event["id"]
    event_type: str = event["type"]

    if event_id in _seen_event_ids:
        logger.info("Duplicate event %s — skipping.", event_id)
        return Response(content="duplicate", status_code=200)
    _seen_event_ids.add(event_id)

    logger.info("Stripe event: %s  id=%s", event_type, event_id)
    obj = event["data"]["object"]

    if event_type == "checkout.session.completed":
        _on_checkout_completed(obj, event_id)
    elif event_type == "invoice.paid":
        _on_invoice_paid(obj, event_id)
    elif event_type == "invoice.payment_failed":
        _on_invoice_payment_failed(obj, event_id)
    elif event_type == "customer.subscription.updated":
        _on_subscription_updated(obj, event_id)
    elif event_type == "customer.subscription.deleted":
        _on_subscription_deleted(obj, event_id)
    else:
        logger.debug("Unhandled event type %s — returning 200.", event_type)

    return Response(content="ok", status_code=200)


def _on_checkout_completed(obj: Any, event_id: str) -> None:
    """Initial payment done — provision access.
    https://docs.stripe.com/payments/checkout/build-subscriptions
    """
    customer = _f(obj, "customer")
    checkout_mode = _f(obj, "mode")  # 'subscription' | 'payment'
    meta = _f(obj, "metadata", {}) or {}
    tier = _f(meta, "tier", "pro")
    logger.info(
        "checkout.session.completed customer=%s sub=%s mode=%s tier=%s event=%s",
        customer, _f(obj, "subscription"), checkout_mode, tier, event_id,
    )
    # Provision access. One-time (payment mode) -> lifetime grant; subscription
    # -> active until first invoice.paid sets the period window.
    entitlements.grant(
        customer, tier, status="active", source_event=event_id,
        lifetime=(checkout_mode == "payment"),
    )


def _on_invoice_paid(obj: Any, event_id: str) -> None:
    """Renewal paid — extend access period.
    Primary event for SaaS billing; fires on initial AND renewal payments.
    https://docs.stripe.com/billing/subscriptions/webhooks
    """
    lines_data = _f(_f(obj, "lines", {}), "data", [])
    period_end = _f(_f(lines_data[0] if lines_data else {}, "period", {}), "end")
    customer = _f(obj, "customer")
    logger.info(
        "invoice.paid customer=%s sub=%s period_end=%s event=%s",
        customer, _f(obj, "subscription"), period_end, event_id,
    )
    entitlements.extend(customer, str(period_end) if period_end else None, source_event=event_id)


def _on_invoice_payment_failed(obj: Any, event_id: str) -> None:
    """Payment failed — email customer, soft-suspend after threshold.
    https://docs.stripe.com/billing/subscriptions/webhooks#payment-failures
    """
    customer = _f(obj, "customer")
    logger.warning(
        "invoice.payment_failed customer=%s attempts=%s next_attempt=%s event=%s",
        customer, _f(obj, "attempt_count", 0),
        _f(obj, "next_payment_attempt"), event_id,
    )
    entitlements.mark_status(customer, "past_due", source_event=event_id)
    # TODO: send payment-failure email with customer portal link.


def _on_subscription_updated(obj: Any, event_id: str) -> None:
    """Plan/status changed — update entitlements.
    https://docs.stripe.com/billing/subscriptions/webhooks
    """
    customer = _f(obj, "customer")
    status = _f(obj, "status")  # active | past_due | canceled | ...
    logger.info(
        "customer.subscription.updated customer=%s status=%s cancel_at_end=%s event=%s",
        customer, status, _f(obj, "cancel_at_period_end"), event_id,
    )
    if status:
        entitlements.mark_status(customer, str(status), source_event=event_id)


def _on_subscription_deleted(obj: Any, event_id: str) -> None:
    """Subscription cancelled — revoke access.
    Fires immediately, or at period end if cancel_at_period_end=True.
    https://docs.stripe.com/billing/subscriptions/webhooks#cancellations
    """
    customer = _f(obj, "customer")
    logger.info(
        "customer.subscription.deleted customer=%s ended_at=%s event=%s",
        customer, _f(obj, "ended_at"), event_id,
    )
    entitlements.revoke(customer, source_event=event_id)
