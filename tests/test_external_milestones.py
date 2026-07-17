"""Principle V (Honest Uncertainty) as code — external milestones NEVER advance on
expectation. They advance ONLY on authoritative, present, and fresh evidence.

Proves:
  * missing OR stale ASC evidence -> BLOCKED_EXTERNAL (never APPROVED)
  * a fresh approval ASC state -> APPLE_APPROVED / READY_FOR_RELEASE / LIVE
  * an unrecognized ASC state fails CLOSED to BLOCKED_EXTERNAL
  * a pending Stripe charge -> PAYMENT_AUTHORIZED (never SETTLED)
  * only balance_txn 'available' -> SETTLED, and booked -> REVENUE_VERIFIED
  * a mismatched settlement charge_id is ignored (fails closed)
  * every advance requires the evidence field present + fresh
"""
from __future__ import annotations

import importlib
import json
import time
from pathlib import Path

import pytest

import backend.truth.external_milestones as em


def _iso(offset_seconds: float = 0.0) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ",
                         time.gmtime(time.time() + offset_seconds))


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """Redirect every evidence source into a temp dir so tests never touch real state."""
    asc = tmp_path / "asc_epic_fury.json"
    stripe = tmp_path / "stripe_settlement.json"
    registry = tmp_path / "product_registry.json"
    monkeypatch.setattr(em, "ASC_EVIDENCE", asc)
    monkeypatch.setattr(em, "STRIPE_EVIDENCE", stripe)
    monkeypatch.setattr(em, "PRODUCT_REGISTRY", registry)
    # a real-charge, pending-settlement registry (mirrors EPIC_FURY_2026 today)
    registry.write_text(json.dumps({"products": [{
        "product_id": "EPIC_FURY_2026",
        "revenue_state": "PENDING_SETTLEMENT",
        "stripe_charge_id": "ch_TEST_123",
        "settles_at": "2026-07-21",
        "revenue_settled_usd": 0,
    }]}))
    return {"asc": asc, "stripe": stripe, "registry": registry}


# ---------------------------------------------------------------------------------
# RELEASE machine
# ---------------------------------------------------------------------------------
def test_missing_asc_evidence_is_blocked_external(sandbox):
    r = em.compute_release()
    assert r["current_state"] == "BLOCKED_EXTERNAL"
    assert r["is_blocked_external"] is True
    assert r["evidence_present"] is False
    assert r["reason"] == "no fresh ASC evidence"
    # NEVER APPROVED without evidence
    assert r["current_state"] != "APPLE_APPROVED"


def test_stale_asc_evidence_never_approves(sandbox):
    # An APPROVED state, but observed a week ago -> stale -> fails closed.
    sandbox["asc"].write_text(json.dumps({
        "versionString": "1.0.2",
        "appStoreState": "APPROVED",
        "observed_at": _iso(-7 * 24 * 3600),
    }))
    r = em.compute_release()
    assert r["current_state"] == "BLOCKED_EXTERNAL"
    assert r["is_stale"] is True
    assert r["current_state"] != "APPLE_APPROVED"
    assert r["freshness_seconds"] > em.ASC_FRESH_SECONDS


def test_in_review_asc_state_is_blocked_external(sandbox):
    sandbox["asc"].write_text(json.dumps({
        "versionString": "1.0.2",
        "appStoreState": "IN_REVIEW",
        "observed_at": _iso(),
    }))
    r = em.compute_release()
    assert r["current_state"] == "BLOCKED_EXTERNAL"
    assert r["app_store_state"] == "IN_REVIEW"


def test_unknown_asc_state_fails_closed(sandbox):
    sandbox["asc"].write_text(json.dumps({
        "versionString": "1.0.2",
        "appStoreState": "SOME_NEW_APPLE_STATE",
        "observed_at": _iso(),
    }))
    r = em.compute_release()
    assert r["current_state"] == "BLOCKED_EXTERNAL"  # never leaks an approval


def test_fresh_approved_advances_to_apple_approved(sandbox):
    sandbox["asc"].write_text(json.dumps({
        "versionString": "1.0.2",
        "appStoreState": "APPROVED",
        "observed_at": _iso(),
    }))
    r = em.compute_release()
    assert r["current_state"] == "APPLE_APPROVED"
    assert r["is_blocked_external"] is False
    assert r["evidence_present"] is True


def test_pending_developer_release_is_ready_for_release(sandbox):
    sandbox["asc"].write_text(json.dumps({
        "versionString": "1.0.2",
        "appStoreState": "PENDING_DEVELOPER_RELEASE",
        "observed_at": _iso(),
    }))
    r = em.compute_release()
    assert r["current_state"] == "READY_FOR_RELEASE"


def test_ready_for_sale_is_live(sandbox):
    sandbox["asc"].write_text(json.dumps({
        "versionString": "1.0.2",
        "appStoreState": "READY_FOR_SALE",
        "observed_at": _iso(),
    }))
    r = em.compute_release()
    assert r["current_state"] == "LIVE"
    assert r["next_transition"] is None  # terminal


# ---------------------------------------------------------------------------------
# REVENUE machine
# ---------------------------------------------------------------------------------
def test_pending_charge_is_payment_authorized_not_settled(sandbox):
    # No settlement evidence at all -> charge authorized, NOT settled.
    r = em.compute_revenue()
    assert r["current_state"] == "PAYMENT_AUTHORIZED"
    assert r["current_state"] != "SETTLED"
    assert r["is_blocked_external"] is True
    assert r["stripe_charge_id"] == "ch_TEST_123"


def test_pending_balance_txn_is_payment_authorized(sandbox):
    # Evidence present but the balance transaction is still 'pending'.
    sandbox["stripe"].write_text(json.dumps({
        "charge_id": "ch_TEST_123",
        "balance_txn_status": "pending",
        "settled_usd": 0,
        "observed_at": _iso(),
    }))
    r = em.compute_revenue()
    assert r["current_state"] == "PAYMENT_AUTHORIZED"
    assert r["current_state"] != "SETTLED"
    assert r["balance_txn_status"] == "pending"


def test_mismatched_charge_id_is_ignored(sandbox):
    # 'available' — but for a DIFFERENT charge. Must fail closed.
    sandbox["stripe"].write_text(json.dumps({
        "charge_id": "ch_SOMEONE_ELSE",
        "balance_txn_status": "available",
        "settled_usd": 18.10,
        "observed_at": _iso(),
    }))
    r = em.compute_revenue()
    assert r["current_state"] == "PAYMENT_AUTHORIZED"


def test_available_balance_txn_is_settled(sandbox):
    # Available, but the amount is not yet booked into the registry -> SETTLED, not verified.
    sandbox["stripe"].write_text(json.dumps({
        "charge_id": "ch_TEST_123",
        "balance_txn_status": "available",
        "settled_usd": 18.10,
        "observed_at": _iso(),
    }))
    r = em.compute_revenue()
    assert r["current_state"] == "SETTLED"
    assert r["is_blocked_external"] is False
    assert r["evidence_present"] is True


def test_available_and_booked_is_revenue_verified(sandbox):
    sandbox["registry"].write_text(json.dumps({"products": [{
        "product_id": "EPIC_FURY_2026",
        "revenue_state": "EARNING",
        "stripe_charge_id": "ch_TEST_123",
        "settles_at": "2026-07-21",
        "revenue_settled_usd": 18.10,
    }]}))
    sandbox["stripe"].write_text(json.dumps({
        "charge_id": "ch_TEST_123",
        "balance_txn_status": "available",
        "settled_usd": 18.10,
        "observed_at": _iso(),
    }))
    r = em.compute_revenue()
    assert r["current_state"] == "REVENUE_VERIFIED"
    assert r["next_transition"] is None  # terminal


def test_no_charge_is_checkout_created(sandbox):
    sandbox["registry"].write_text(json.dumps({"products": [{
        "product_id": "EPIC_FURY_2026",
        "revenue_state": "NOT_STARTED",
    }]}))
    r = em.compute_revenue()
    assert r["current_state"] == "CHECKOUT_CREATED"


# ---------------------------------------------------------------------------------
# transitions require the evidence field
# ---------------------------------------------------------------------------------
def test_every_non_terminal_state_names_its_required_evidence(sandbox):
    for state in ("BLOCKED_EXTERNAL", "APPLE_APPROVED", "READY_FOR_RELEASE"):
        nxt = em._release_next(state)
        assert nxt is not None
        assert nxt["requires_evidence"]  # non-empty
    for state in ("CHECKOUT_CREATED", "PAYMENT_AUTHORIZED", "SETTLED"):
        nxt = em._revenue_next(state)
        assert nxt is not None
        assert nxt["requires_evidence"]
    assert em._release_next("LIVE") is None
    assert em._revenue_next("REVENUE_VERIFIED") is None


def test_top_level_envelope_shape(sandbox):
    out = em.compute_external_milestones()
    assert out["truth_class"] == "HELM_EXTERNAL_MILESTONES"
    assert set(out["milestones"]) == {"RELEASE", "REVENUE"}
    assert out["doctrine"]["fails_closed"] is True
    # honest current state under the sandbox: blocked release, authorized-not-settled revenue
    assert out["milestones"]["RELEASE"]["current_state"] == "BLOCKED_EXTERNAL"
    assert out["milestones"]["REVENUE"]["current_state"] == "PAYMENT_AUTHORIZED"
