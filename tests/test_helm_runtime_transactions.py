"""HELM runtime substrate: governance, transactions, events, truth-not-a-role."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.helm_runtime.governance_engine import (
    normalize_role,
    role_may_write,
    validate_proposal,
)
from backend.helm_runtime.event_bus import publish_event, tail_events
from backend.helm_runtime.transaction import MissionTransaction, commit_proposal
from backend.helm_runtime.mission_runtime import mission_projection_hint


def test_truth_and_runtime_are_not_roles():
    assert normalize_role("truth").startswith("INVALID_")
    assert normalize_role("runtime").startswith("INVALID_")
    ok, errs = validate_proposal("truth", {"mission.routing": "x"})
    assert ok is False


def test_orchestrator_may_plan_not_audit():
    assert role_may_write("orchestrator", "mission.planning") or role_may_write(
        "orchestrator", "mission.task_queue"
    )
    assert role_may_write("orchestrator", "mission.auditor_verdict") is False
    assert role_may_write("builder", "mission.engineering_status") is True
    assert role_may_write("auditor", "mission.red_team_results") or role_may_write(
        "auditor", "mission.auditor_verdict"
    )


def test_transaction_commit_and_event(tmp_path, monkeypatch):
    src = Path("coordination/goal/executive_mission.json")
    doc = json.loads(src.read_text())
    doc["mission_version"] = 10
    doc["parent_version"] = 9
    p = tmp_path / "executive_mission.json"
    p.write_text(json.dumps(doc, indent=2))
    ev_path = tmp_path / "events.jsonl"

    # point event bus path
    import backend.helm_runtime.event_bus as eb
    import backend.helm_runtime.transaction as tx

    monkeypatch.setattr(eb, "EVENTS_PATH", ev_path)
    monkeypatch.setattr(tx, "EXEC_PATH", p)

    result = MissionTransaction(
        "builder",
        {"mission.engineering_status": "IN_PROGRESS"},
        path=p,
        recompute_truth=False,
        note="unit test",
        correlation_id="TX-TEST-1",
        actor="Claude",
    ).run()
    assert result["ok"] is True
    assert result["mission_version"] == 11
    assert result["parent_version"] == 10
    reloaded = json.loads(p.read_text())
    assert reloaded["mission_version"] == 11
    assert reloaded["transaction_id"] == result["transaction_id"]
    assert ev_path.exists()
    events = [json.loads(l) for l in ev_path.read_text().splitlines() if l.strip()]
    assert events[-1]["type"] == "MISSION_TRANSACTION_COMMITTED"


def test_builder_cannot_write_auditor_verdict(tmp_path):
    src = Path("coordination/goal/executive_mission.json")
    doc = json.loads(src.read_text())
    p = tmp_path / "executive_mission.json"
    p.write_text(json.dumps(doc, indent=2))
    result = MissionTransaction(
        "builder",
        {"mission.auditor_verdict": "VERIFIED"},
        path=p,
        recompute_truth=False,
    ).run()
    assert result["ok"] is False
    assert result.get("phase") == "VALIDATE"


def test_projection_hint_says_dashboard_not_source():
    h = mission_projection_hint()
    assert h["doctrine"] == "dashboard_is_projection_never_source"
    assert h["platform"]["is_actor"] is False
