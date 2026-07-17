"""Evidence-triggered EXTERNAL-MILESTONE tracker.

HELM Design Constitution — Principle V (Honest Uncertainty) AS CODE.

An external milestone is one HELM cannot make true by itself: Apple must approve a
build; Stripe must settle a charge. HELM does not *own* these transitions, so it must
never *assert* them. This module holds every external milestone at BLOCKED_EXTERNAL
(or its revenue analogue, PAYMENT_AUTHORIZED) and advances it ONLY when an
AUTHORITATIVE evidence snapshot — written by a Mac-side poller/watcher against the real
provider — confirms the transition. Expectation is not evidence. A settle date is not a
settlement. "Founder says approved" is not an ASC state.

NEVER advance a machine without an evidence field that is PRESENT and FRESH.
Absent, stale, or mismatched evidence fails CLOSED to the held state.

Two machines:
  RELEASE  (Epic Fury on the App Store):
      BLOCKED_EXTERNAL -> APPLE_APPROVED -> READY_FOR_RELEASE -> LIVE
      driven by  coordination/evidence/external/asc_epic_fury.json
                 {versionString, appStoreState, observed_at}  (Mac-side ASC poller)
  REVENUE  (Epic Fury first settled dollar):
      CHECKOUT_CREATED -> PAYMENT_AUTHORIZED -> SETTLED -> REVENUE_VERIFIED
      driven by  coordination/products/product_registry.json  (EPIC_FURY_2026)
             +   coordination/evidence/external/stripe_settlement.json (optional)
                 {charge_id, balance_txn_status, settled_usd, observed_at}
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

# --- evidence sources ---------------------------------------------------------------
ASC_EVIDENCE = ROOT / "coordination" / "evidence" / "external" / "asc_epic_fury.json"
STRIPE_EVIDENCE = ROOT / "coordination" / "evidence" / "external" / "stripe_settlement.json"
PRODUCT_REGISTRY = ROOT / "coordination" / "products" / "product_registry.json"

EPIC_FURY_PRODUCT_ID = "EPIC_FURY_2026"

# --- freshness windows --------------------------------------------------------------
# ASC state moves on Apple's clock; a poller that runs at least a few times a day keeps
# this fresh. Evidence older than the window is treated as STALE -> fail closed.
ASC_FRESH_SECONDS = 6 * 3600            # 6 hours
# A settlement is a terminal fact — once a balance transaction is "available" it stays
# available. We still record freshness, but a stale settlement snapshot is NOT demoted:
# the fact does not un-happen. We do require the snapshot be present, parseable, and
# report its age honestly.
SETTLEMENT_FRESH_SECONDS = 14 * 24 * 3600   # 14 days (reported; not a demotion gate)


# ===================================================================================
# helpers
# ===================================================================================
def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _parse_iso(ts: str | None) -> float | None:
    """Parse an ISO-8601 timestamp to epoch seconds. Returns None if unparseable."""
    if not ts or not isinstance(ts, str):
        return None
    s = ts.strip().replace("Z", "+00:00")
    try:
        import datetime as _dt
        return _dt.datetime.fromisoformat(s).timestamp()
    except Exception:
        return None


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _freshness_seconds(observed_at: str | None, path: Path) -> float | None:
    """Age of the evidence, preferring the poller's observed_at over file mtime.

    Returns None when we cannot establish an age at all (no observed_at, no file)."""
    epoch = _parse_iso(observed_at)
    if epoch is not None:
        return max(0.0, time.time() - epoch)
    if path.exists():
        return max(0.0, time.time() - path.stat().st_mtime)
    return None


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except Exception:
        return str(path)


# ===================================================================================
# RELEASE machine — Epic Fury App Store
# ===================================================================================
RELEASE_STATES = ["BLOCKED_EXTERNAL", "APPLE_APPROVED", "READY_FOR_RELEASE", "LIVE"]

# Authoritative App Store Connect appStoreState -> HELM RELEASE state.
# The specific approval PENDINGs (developer/apple release) are APPROVAL states and take
# precedence over the generic "PENDING_* -> BLOCKED" rule.
ASC_LIVE = {"READY_FOR_SALE"}
ASC_READY_FOR_RELEASE = {"PENDING_DEVELOPER_RELEASE", "PENDING_APPLE_RELEASE"}
ASC_APPROVED = {"APPROVED"}
# Everything review/prep/reject/other-pending holds the milestone closed. This set is
# documentary; ANY state not in the three advance sets above fails closed to
# BLOCKED_EXTERNAL, so an unknown/new Apple state can never leak an approval.
ASC_BLOCKED = {
    "PREPARE_FOR_SUBMISSION", "WAITING_FOR_REVIEW", "IN_REVIEW",
    "WAITING_FOR_EXPORT_COMPLIANCE", "PENDING_CONTRACT", "PROCESSING_FOR_APP_STORE",
    "METADATA_REJECTED", "REJECTED", "DEVELOPER_REJECTED", "INVALID_BINARY",
    "REMOVED_FROM_SALE", "DEVELOPER_REMOVED_FROM_SALE", "REPLACED_WITH_NEW_VERSION",
    "NOT_APPLICABLE",
}


def _release_next(state: str) -> dict[str, Any] | None:
    """The next transition and the EXACT evidence that would trigger it. None if terminal."""
    triggers = {
        "BLOCKED_EXTERNAL": {
            "to": "APPLE_APPROVED",
            "requires_evidence":
                f"{_rel(ASC_EVIDENCE)} fresh (< {ASC_FRESH_SECONDS}s) with "
                f"appStoreState in {sorted(ASC_APPROVED | ASC_READY_FOR_RELEASE)}",
        },
        "APPLE_APPROVED": {
            "to": "READY_FOR_RELEASE",
            "requires_evidence":
                f"{_rel(ASC_EVIDENCE)} appStoreState in {sorted(ASC_READY_FOR_RELEASE)} "
                "(Apple approved; awaiting the release control)",
        },
        "READY_FOR_RELEASE": {
            "to": "LIVE",
            "requires_evidence":
                f"{_rel(ASC_EVIDENCE)} appStoreState == 'READY_FOR_SALE'",
        },
    }
    return triggers.get(state)


def compute_release() -> dict[str, Any]:
    """RELEASE machine — derived SOLELY from the authoritative ASC evidence snapshot.

    Fails closed to BLOCKED_EXTERNAL when the snapshot is missing, stale, or its
    appStoreState is anything other than an explicit approval/live state.
    """
    ev = _load_json(ASC_EVIDENCE)
    fresh = _freshness_seconds(ev.get("observed_at") if ev else None, ASC_EVIDENCE)

    # --- fail closed: no evidence at all -------------------------------------------
    if ev is None:
        state = "BLOCKED_EXTERNAL"
        return {
            "machine": "RELEASE",
            "label": "Epic Fury — App Store release",
            "states": RELEASE_STATES,
            "current_state": state,
            "is_blocked_external": True,
            "reason": "no fresh ASC evidence",
            "evidence_present": False,
            "evidence_source": _rel(ASC_EVIDENCE),
            "app_store_state": None,
            "version_string": None,
            "observed_at": None,
            "freshness_seconds": fresh,   # None -> genuinely unknown
            "is_stale": None,
            "next_transition": _release_next(state),
        }

    app_state = ev.get("appStoreState")
    version = ev.get("versionString")
    is_stale = fresh is None or fresh > ASC_FRESH_SECONDS

    # --- fail closed: evidence is stale --------------------------------------------
    if is_stale:
        state = "BLOCKED_EXTERNAL"
        return {
            "machine": "RELEASE",
            "label": "Epic Fury — App Store release",
            "states": RELEASE_STATES,
            "current_state": state,
            "is_blocked_external": True,
            "reason": "no fresh ASC evidence",
            "detail": f"ASC snapshot present but stale (> {ASC_FRESH_SECONDS}s old); "
                      "an external milestone never advances on stale evidence",
            "evidence_present": True,
            "evidence_source": _rel(ASC_EVIDENCE),
            "app_store_state": app_state,
            "version_string": version,
            "observed_at": ev.get("observed_at"),
            "freshness_seconds": fresh,
            "is_stale": True,
            "next_transition": _release_next(state),
        }

    # --- fresh evidence: map the authoritative appStoreState -----------------------
    if app_state in ASC_LIVE:
        state, reason = "LIVE", f"ASC appStoreState == {app_state}"
    elif app_state in ASC_READY_FOR_RELEASE:
        state, reason = "READY_FOR_RELEASE", \
            f"Apple approved; ASC appStoreState == {app_state} (awaiting release control)"
    elif app_state in ASC_APPROVED:
        state, reason = "APPLE_APPROVED", f"ASC appStoreState == {app_state}"
    else:
        # Review, prep, rejection, or any unknown/new Apple state -> fail closed.
        state = "BLOCKED_EXTERNAL"
        known = "review/prep/rejection" if app_state in ASC_BLOCKED else "unrecognized"
        reason = f"ASC appStoreState == {app_state} ({known}); not an approval state"

    return {
        "machine": "RELEASE",
        "label": "Epic Fury — App Store release",
        "states": RELEASE_STATES,
        "current_state": state,
        "is_blocked_external": state == "BLOCKED_EXTERNAL",
        "reason": reason,
        "evidence_present": True,
        "evidence_source": _rel(ASC_EVIDENCE),
        "app_store_state": app_state,
        "version_string": version,
        "observed_at": ev.get("observed_at"),
        "freshness_seconds": fresh,
        "is_stale": False,
        "next_transition": _release_next(state),
    }


# ===================================================================================
# REVENUE machine — Epic Fury first settled dollar
# ===================================================================================
REVENUE_STATES = ["CHECKOUT_CREATED", "PAYMENT_AUTHORIZED", "SETTLED", "REVENUE_VERIFIED"]


def _epic_fury_registry() -> dict[str, Any]:
    reg = _load_json(PRODUCT_REGISTRY) or {}
    for p in reg.get("products", []) or []:
        if isinstance(p, dict) and p.get("product_id") == EPIC_FURY_PRODUCT_ID:
            return p
    return {}


def _revenue_next(state: str) -> dict[str, Any] | None:
    triggers = {
        "CHECKOUT_CREATED": {
            "to": "PAYMENT_AUTHORIZED",
            "requires_evidence":
                "product_registry EPIC_FURY_2026.stripe_charge_id present "
                "(a real charge was authorized)",
        },
        "PAYMENT_AUTHORIZED": {
            "to": "SETTLED",
            "requires_evidence":
                f"{_rel(STRIPE_EVIDENCE)} with charge_id matching the registry charge AND "
                "balance_txn_status == 'available' (Stripe balance transaction settled)",
        },
        "SETTLED": {
            "to": "REVENUE_VERIFIED",
            "requires_evidence":
                "settlement evidence settled_usd > 0 AND registry revenue_settled_usd > 0 "
                "(settled amount booked into the registry)",
        },
    }
    return triggers.get(state)


def compute_revenue() -> dict[str, Any]:
    """REVENUE machine — a charge is PAYMENT_AUTHORIZED, NOT settled, until an
    authoritative Stripe balance-transaction status of 'available' proves settlement.

    A pending charge, a settle *date*, or a mismatched/absent settlement snapshot all
    hold the milestone at PAYMENT_AUTHORIZED. Expectation is not evidence.
    """
    reg = _epic_fury_registry()
    charge_id = reg.get("stripe_charge_id")
    reg_settled_usd = reg.get("revenue_settled_usd")
    settles_at = reg.get("settles_at")
    reg_revenue_state = reg.get("revenue_state")

    ev = _load_json(STRIPE_EVIDENCE)
    fresh = _freshness_seconds(ev.get("observed_at") if ev else None, STRIPE_EVIDENCE)

    # --- no charge yet -------------------------------------------------------------
    if not charge_id:
        state = "CHECKOUT_CREATED"
        return {
            "machine": "REVENUE",
            "label": "Epic Fury — first settled dollar",
            "states": REVENUE_STATES,
            "current_state": state,
            "is_blocked_external": True,
            "reason": "no charge on record; awaiting a real customer payment",
            "evidence_present": False,
            "evidence_source": _rel(PRODUCT_REGISTRY),
            "stripe_charge_id": None,
            "settles_at": settles_at,
            "registry_revenue_state": reg_revenue_state,
            "registry_revenue_settled_usd": reg_settled_usd,
            "balance_txn_status": None,
            "settled_usd": None,
            "observed_at": None,
            "freshness_seconds": None,
            "next_transition": _revenue_next(state),
        }

    # --- charge exists: default hold at PAYMENT_AUTHORIZED --------------------------
    # A charge being taken proves authorization, NOT settlement. We only advance when
    # authoritative settlement evidence says the balance transaction is 'available'.
    state = "PAYMENT_AUTHORIZED"
    reason = ("charge authorized but not proven settled; awaiting Stripe "
              f"balance-transaction 'available' (settle date on file: {settles_at})")
    balance_status = None
    settled_usd = None
    evidence_present = False
    evidence_source = _rel(PRODUCT_REGISTRY)
    observed_at = None

    if ev is not None:
        ev_charge = ev.get("charge_id")
        balance_status = ev.get("balance_txn_status")
        settled_usd = ev.get("settled_usd")
        observed_at = ev.get("observed_at")
        if ev_charge != charge_id:
            # Mismatched evidence is NOT this charge's settlement — fail closed.
            reason = (f"settlement evidence charge_id {ev_charge!r} does not match "
                      f"registry charge {charge_id!r}; ignored — still PAYMENT_AUTHORIZED")
        elif balance_status == "available":
            evidence_present = True
            evidence_source = _rel(STRIPE_EVIDENCE)
            state = "SETTLED"
            reason = "Stripe balance transaction is 'available' — funds settled"
            # REVENUE_VERIFIED requires the settled amount be booked into the registry.
            try:
                booked = float(reg_settled_usd) if reg_settled_usd is not None else 0.0
            except (TypeError, ValueError):
                booked = 0.0
            try:
                ev_amount = float(settled_usd) if settled_usd is not None else 0.0
            except (TypeError, ValueError):
                ev_amount = 0.0
            if ev_amount > 0 and booked > 0:
                state = "REVENUE_VERIFIED"
                reason = ("Stripe settlement 'available' AND settled amount booked "
                          f"into the registry (${booked:.2f})")
        else:
            # Evidence present but pending/other -> still authorized, not settled.
            evidence_source = _rel(STRIPE_EVIDENCE)
            reason = (f"settlement evidence present but balance_txn_status == "
                      f"{balance_status!r} (not 'available'); a pending charge is "
                      "PAYMENT_AUTHORIZED, not SETTLED")

    return {
        "machine": "REVENUE",
        "label": "Epic Fury — first settled dollar",
        "states": REVENUE_STATES,
        "current_state": state,
        "is_blocked_external": state in ("CHECKOUT_CREATED", "PAYMENT_AUTHORIZED"),
        "reason": reason,
        "evidence_present": evidence_present,
        "evidence_source": evidence_source,
        "stripe_charge_id": charge_id,
        "settles_at": settles_at,
        "registry_revenue_state": reg_revenue_state,
        "registry_revenue_settled_usd": reg_settled_usd,
        "balance_txn_status": balance_status,
        "settled_usd": settled_usd,
        "observed_at": observed_at,
        "freshness_seconds": fresh,
        "next_transition": _revenue_next(state),
    }


# ===================================================================================
# top-level
# ===================================================================================
def compute_external_milestones() -> dict[str, Any]:
    """Both external-milestone state machines, each derived independently from its own
    authoritative evidence. Held closed until evidence — present AND fresh — advances it.
    """
    t0 = time.time()
    release = compute_release()
    revenue = compute_revenue()

    # Overall freshness: the oldest known evidence age across machines (None if neither
    # has a measurable age — we do not fabricate a "0s, so fresh").
    ages = [m.get("freshness_seconds") for m in (release, revenue)
            if isinstance(m.get("freshness_seconds"), (int, float))]
    freshness = max(ages) if ages else None

    return {
        "truth_class": "HELM_EXTERNAL_MILESTONES",
        "source": "backend.truth.external_milestones",
        "observed_at": _now(),
        "freshness_seconds": freshness,
        "milestones": {
            "RELEASE": release,
            "REVENUE": revenue,
        },
        "doctrine": {
            "principle": "V — Honest Uncertainty (as code)",
            "rule": "External milestones hold at BLOCKED_EXTERNAL and advance ONLY on "
                    "authoritative, present, and fresh evidence — never on expectation.",
            "asc_fresh_seconds": ASC_FRESH_SECONDS,
            "settlement_gate": "balance_txn_status == 'available'",
            "fails_closed": True,
            "evidence_dir": _rel(ASC_EVIDENCE.parent),
        },
        "build_ms": int((time.time() - t0) * 1000),
    }


if __name__ == "__main__":
    print(json.dumps(compute_external_milestones(), indent=2))
