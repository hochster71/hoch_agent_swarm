"""Billing mode guard — fail-closed to TEST.

The single source of truth for "are we allowed to charge, and in which mode?".

Safety contract (why this exists):
  * Nothing may EVER take a real card charge until the founder explicitly throws
    the live switch. That requires BOTH conditions, not one:
      1. STRIPE_SECRET_KEY is a live key (sk_live_...)
      2. HASF_BILLING_LIVE=1 is set in the environment
  * A live key present WITHOUT the switch => "test_locked": we refuse to create
    live sessions and surface a clear 409 telling the founder to throw the switch.
    This prevents an accidental live charge the moment live keys land in .env.
  * No key at all => "disabled": billing endpoints return 503, no crash.

Ref: Stripe test vs live modes — https://docs.stripe.com/keys#test-live-modes
"""
from __future__ import annotations

import os

MODE_TEST = "test"
MODE_LIVE = "live"
MODE_TEST_LOCKED = "test_locked"  # live key present, founder switch OFF -> block live
MODE_DISABLED = "disabled"        # no usable key


def key_mode() -> str:
    """Classify the configured secret key by prefix only (never returns the value)."""
    sk = os.environ.get("STRIPE_SECRET_KEY", "").strip()
    if sk.startswith("sk_live_"):
        return MODE_LIVE
    if sk.startswith("sk_test_"):
        return MODE_TEST
    return "unset"


def live_switch_on() -> bool:
    """The founder's explicit go-live switch. Off by default."""
    return os.environ.get("HASF_BILLING_LIVE", "0").strip() == "1"


def effective_mode() -> str:
    """Resolve the mode the system is actually allowed to operate in."""
    km = key_mode()
    if km == "unset":
        return MODE_DISABLED
    if km == MODE_LIVE:
        return MODE_LIVE if live_switch_on() else MODE_TEST_LOCKED
    return MODE_TEST  # test key -> always safe test mode


def can_charge() -> bool:
    """True only when a checkout session may be created right now."""
    return effective_mode() in (MODE_TEST, MODE_LIVE)


def stripe_price_field() -> str:
    """Which price-id field the catalog should resolve for the effective mode."""
    return "live_price_id" if effective_mode() == MODE_LIVE else "test_price_id"


def status() -> dict:
    """Ops/widget-friendly snapshot. Never exposes key material."""
    return {
        "key_mode": key_mode(),
        "live_switch_on": live_switch_on(),
        "effective_mode": effective_mode(),
        "can_charge": can_charge(),
        "note": {
            MODE_TEST: "Test mode — no real cards can be charged.",
            MODE_LIVE: "LIVE — real cards will be charged.",
            MODE_TEST_LOCKED: "Live key detected but founder switch OFF — live charges blocked until HASF_BILLING_LIVE=1.",
            MODE_DISABLED: "No Stripe key configured — billing disabled.",
        }[effective_mode()],
    }
