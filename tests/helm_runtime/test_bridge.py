"""Tests for the HELM Runtime Bridge — OCC store, provider router, role router.

Grok (Auditor) owns the authoritative adversarial pass; these are the Builder's
own regression + negative tests proving the door is closed by construction.

Uses a temp copy of executive_mission.json so the real mission is never touched.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.helm_runtime import (
    mission_store,
    provider_router,
    role_router,
)
from backend.helm_runtime import event_bus as eb

ROOT = Path(__file__).resolve().parents[2]
REAL_EXEC = ROOT / "coordination" / "goal" / "executive_mission.json"


@pytest.fixture()
def temp_mission(tmp_path, monkeypatch):
    """Isolated mission + event bus so tests never mutate real runtime state."""
    doc = json.loads(REAL_EXEC.read_text(encoding="utf-8"))
    p = tmp_path / "executive_mission.json"
    p.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    events = tmp_path / "helm_events.jsonl"
    # Point the event bus at the temp log; disable truth recompute side-effects.
    monkeypatch.setattr(eb, "EVENTS_PATH", events, raising=True)
    return p


# ---- Optimistic concurrency (compare-and-swap) --------------------------------

def test_commit_with_correct_version_lands(temp_mission):
    v = mission_store.current_version(path=temp_mission)
    r = mission_store.compare_and_swap(
        "builder",
        {"engineering.smoke": "ok"},
        v,
        path=temp_mission,
        recompute_truth=False,
    )
    assert r["ok"] is True
    assert r["status"] == "END"
    assert r["mission_version"] == v + 1


def test_stale_version_is_rejected(temp_mission):
    v = mission_store.current_version(path=temp_mission)
    # First writer bumps the version.
    ok = mission_store.compare_and_swap(
        "builder", {"engineering.first": 1}, v, path=temp_mission, recompute_truth=False
    )
    assert ok["ok"] is True
    # Second writer still holds the OLD version -> CONFLICT, no clobber.
    stale = mission_store.compare_and_swap(
        "auditor", {"assurance.second": 2}, v, path=temp_mission, recompute_truth=False
    )
    assert stale["ok"] is False
    assert stale["status"] == "CONFLICT"
    assert stale["actual_parent_version"] == v + 1
    # And the first writer's value survived.
    doc = json.loads(temp_mission.read_text())
    assert doc["engineering"]["first"] == 1
    assert "second" not in doc.get("assurance", {})


# ---- Role router: the single door --------------------------------------------

def test_route_rejects_non_actor_roles(temp_mission):
    for bad in ("truth", "runtime", "nobody"):
        r = role_router.route_proposal(bad, {"engineering.x": 1}, path=temp_mission)
        assert r["ok"] is False
        assert r["status"] == "ROLE_REJECTED"


def test_route_pins_version_automatically(temp_mission):
    # No expected_parent_version supplied -> router pins to current on read.
    r = role_router.route_proposal(
        "builder", {"engineering.auto": True}, path=temp_mission, recompute_truth=False
    )
    assert r["ok"] is True
    assert r["status"] == "END"


# ---- Negative tests: governance is enforced through the door ------------------

def test_auditor_cannot_write_builder_field(temp_mission):
    v = mission_store.current_version(path=temp_mission)
    r = role_router.route_proposal(
        "auditor",
        {"engineering.status": "green"},  # builder-owned namespace
        expected_parent_version=v,
        path=temp_mission,
        recompute_truth=False,
    )
    assert r["ok"] is False
    assert r["status"] == "FAILED"
    assert r["phase"] == "VALIDATE"


def test_founder_gate_requires_founder(temp_mission):
    v = mission_store.current_version(path=temp_mission)
    # Builder attempting a founder-gate field must be denied.
    r = role_router.route_proposal(
        "builder",
        {"money_movement": {"amount": 1}},
        expected_parent_version=v,
        path=temp_mission,
        recompute_truth=False,
    )
    assert r["ok"] is False
    assert r["status"] == "FAILED"


def test_founder_gate_needs_authorization_token(temp_mission):
    v = mission_store.current_version(path=temp_mission)
    # Founder role but NO explicit authorization token -> refused at AUTHORIZE.
    r = role_router.route_proposal(
        "founder",
        {"publish_external": {"target": "app_store"}},
        expected_parent_version=v,
        founder_token_present=False,
        path=temp_mission,
        recompute_truth=False,
    )
    assert r["ok"] is False
    assert r["status"] == "FAILED"
    assert r["phase"] == "AUTHORIZE"


# ---- Provider router: worker-as-plugin, no secrets ----------------------------

def test_resolve_worker_never_returns_secret():
    w = provider_router.resolve_worker("builder")
    assert w["role"] == "builder"
    assert w["provider"] == "anthropic"
    # Must report presence only — never the key value itself.
    assert "key_present" in w
    for k, val in w.items():
        assert "sk-" not in str(val)  # no live secret ever surfaces


def test_truth_and_runtime_are_not_bindable_roles():
    for bad in ("truth", "runtime"):
        w = provider_router.resolve_worker(bad)
        assert w["configured"] is False
        assert w.get("error") == "NOT_A_BINDABLE_ROLE"


def test_worker_health_counts_configured():
    h = provider_router.worker_health()
    assert h["engine"] == "provider_router"
    assert h["is_actor"] is False
    assert h["total_roles"] == 3
    assert 0 <= h["configured_count"] <= 3


# ---- Event emission on commit -------------------------------------------------

def test_commit_emits_event(temp_mission):
    v = mission_store.current_version(path=temp_mission)
    r = mission_store.compare_and_swap(
        "builder", {"engineering.evt": 1}, v, path=temp_mission, recompute_truth=False
    )
    assert r["ok"] is True
    events = eb.tail_events(n=5)
    assert any(e.get("type") == "MISSION_TRANSACTION_COMMITTED" for e in events)
