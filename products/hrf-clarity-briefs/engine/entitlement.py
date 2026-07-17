"""Entitlement gate — wires brief generation behind the checkout pattern.

NO REAL PAYMENT is handled here. This mirrors the checkout shape in
`api/create-checkout-session.js`: a buyer completes Stripe Checkout, a webhook
(founder wires it) records an entitlement token, and this module checks that
token before the engine will generate.

Store format (JSON file, default `entitlements.json`):
    { "tok_abc123": {"tier": "brief", "remaining": 1},
      "sub_xyz789": {"tier": "monthly", "remaining": null} }   # null = unlimited

`remaining: null` = active subscription (unlimited within the period). An integer
= one-off credits. `consume()` decrements one-off credits. Absent/zero = denied.

This is intentionally simple and file-backed so it runs with zero dependencies.
The founder step to make it real is in the README (create Stripe prices, wire the
webhook to write tokens here).
"""

from __future__ import annotations

import json
import os
from typing import Optional


class EntitlementError(Exception):
    pass


class EntitlementStore:
    def __init__(self, path: Optional[str] = None):
        self.path = path or os.environ.get(
            "HRF_ENTITLEMENTS_PATH", "entitlements.json"
        )

    def _load(self) -> dict:
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f) or {}
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self, data: dict) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def is_entitled(self, token: str) -> bool:
        if not token:
            return False
        rec = self._load().get(token)
        if rec is None:
            return False
        remaining = rec.get("remaining", 0)
        return remaining is None or (isinstance(remaining, int) and remaining > 0)

    def consume(self, token: str) -> None:
        """Decrement a one-off credit. Subscriptions (remaining=None) are
        unaffected. Raises if the token is not entitled."""
        data = self._load()
        rec = data.get(token)
        if rec is None:
            raise EntitlementError(f"unknown or unpaid token: {token!r}")
        remaining = rec.get("remaining", 0)
        if remaining is None:
            return  # unlimited subscription
        if not (isinstance(remaining, int) and remaining > 0):
            raise EntitlementError(f"no remaining credits for token: {token!r}")
        rec["remaining"] = remaining - 1
        self._save(data)


def require_entitlement(token: str, store: Optional[EntitlementStore] = None,
                        consume: bool = True) -> None:
    """Raise EntitlementError unless `token` is entitled. Consumes a one-off
    credit by default. Call this before generating a paid brief."""
    store = store or EntitlementStore()
    if not store.is_entitled(token):
        raise EntitlementError(
            "not entitled: complete checkout to obtain a valid entitlement token "
            "(see api/create-checkout-session.js and README)."
        )
    if consume:
        store.consume(token)
