"""Pricing catalog loader + resolver.

Covers the three models the founder selected: freemium (free tier), recurring
subscription (Pro/Team monthly + annual), and one-time purchase (Lifetime).

The catalog never exposes secret key material. It resolves the Stripe price id
for the *effective* billing mode (test vs live) so calling code can't accidentally
use a live price id while in test mode or vice-versa.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from backend.billing import mode as billing_mode

_CATALOG_PATH = Path(__file__).resolve().parent / "pricing_catalog.json"

VALID_KINDS = {"freemium", "subscription", "one_time"}
VALID_CHECKOUT_MODES = {None, "subscription", "payment"}


def load_catalog() -> dict:
    with open(_CATALOG_PATH, "r") as f:
        return json.load(f)


def tiers() -> list[dict]:
    return load_catalog().get("tiers", [])


def get_tier(tier_id: str) -> Optional[dict]:
    for t in tiers():
        if t.get("id") == tier_id:
            return t
    return None


def resolve_price_id(tier: dict) -> Optional[str]:
    """Return the Stripe price id for the current effective mode, or None for free."""
    field = billing_mode.stripe_price_field()  # 'test_price_id' | 'live_price_id'
    return (tier.get("stripe") or {}).get(field)


def public_catalog() -> dict:
    """Catalog safe to hand to a browser: list prices + features, mode banner,
    NO stripe price ids, NO key material."""
    cat = load_catalog()
    m = billing_mode.status()
    return {
        "schema": cat.get("schema"),
        "currency": cat.get("currency"),
        "mode": m["effective_mode"],
        "mode_note": m["note"],
        "tiers": [
            {
                "id": t["id"],
                "name": t["name"],
                "kind": t["kind"],
                "price_usd": t["price_usd"],
                "billing": t["billing"],
                "checkout_mode": t.get("checkout_mode"),
                "features": t.get("features", []),
                "purchasable": bool(resolve_price_id(t)) if t["kind"] != "freemium" else False,
            }
            for t in cat.get("tiers", [])
        ],
    }


def validate() -> list[str]:
    """Structural integrity check. Returns a list of problems (empty == valid)."""
    problems: list[str] = []
    cat = load_catalog()
    ids = set()
    kinds_seen = set()
    for t in cat.get("tiers", []):
        tid = t.get("id")
        if not tid:
            problems.append("tier missing id")
            continue
        if tid in ids:
            problems.append(f"duplicate tier id: {tid}")
        ids.add(tid)
        if t.get("kind") not in VALID_KINDS:
            problems.append(f"{tid}: invalid kind {t.get('kind')!r}")
        kinds_seen.add(t.get("kind"))
        if t.get("checkout_mode") not in VALID_CHECKOUT_MODES:
            problems.append(f"{tid}: invalid checkout_mode {t.get('checkout_mode')!r}")
        # subscription -> checkout_mode subscription; one_time -> payment; freemium -> null
        expect = {"subscription": "subscription", "one_time": "payment", "freemium": None}
        if t.get("checkout_mode") != expect.get(t.get("kind")):
            problems.append(f"{tid}: checkout_mode {t.get('checkout_mode')!r} does not match kind {t.get('kind')!r}")
        # live ids must be null until go-live (guards against premature live wiring in the repo)
        if (t.get("stripe") or {}).get("live_price_id") not in (None, ""):
            problems.append(f"{tid}: live_price_id is set in the committed catalog — live ids belong in .env/founder go-live, not source")
    for required in ("freemium", "subscription", "one_time"):
        if required not in kinds_seen:
            problems.append(f"catalog missing a {required} tier (founder chose all three models)")
    return problems
