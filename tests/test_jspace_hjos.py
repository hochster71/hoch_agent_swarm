"""HJOS — read-only observability swarm tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.jspace.charter import HJOS_CHARTER
from backend.jspace.ledger import JSpaceLedger
from backend.jspace.runner import run_hjos_cycle
from backend.jspace.schema import JSpaceAssessment
from backend.jspace.truth_classes import TruthAssessment


def test_charter_forbids_state_mutation():
    with pytest.raises(PermissionError):
        HJOS_CHARTER.assert_read_only(state_mutated=True)
    HJOS_CHARTER.assert_read_only(state_mutated=False)
    assert HJOS_CHARTER.promotion_authority == "NONE"
    assert HJOS_CHARTER.automatic_quarantine_enabled is False


def test_assessment_rejects_state_mutated():
    with pytest.raises(PermissionError):
        JSpaceAssessment(
            subject="x",
            observer="jspace_truth_sentinel",
            assessment=TruthAssessment.CONFIRMED_LIVE,
            state_mutated=True,
        )


def test_assessment_digest_stable_fields(tmp_path: Path):
    a = JSpaceAssessment(
        subject="task-1",
        observer="jspace_truth_sentinel",
        assessment=TruthAssessment.CONTRADICTED,
        claimed_state="COMPLETED",
        observed_state="LEASE_EXPIRED",
        evidence=["coordination/leases/x.lock"],
        confidence=0.99,
        recommended_action="WITHHOLD_PROMOTION",
        observation_id="JOBS-TEST-000001",
        observed_at="2026-07-14T00:00:00Z",
    )
    d = a.to_dict()
    assert d["state_mutated"] is False
    assert d["assessment"] == "CONTRADICTED"
    assert "assessment_digest" in d
    assert len(d["assessment_digest"]) == 64


def test_cycle_detects_unbound_active_lease(tmp_path: Path):
    repo = tmp_path / "repo"
    leases = repo / "coordination" / "leases"
    leases.mkdir(parents=True)
    council = repo / "coordination" / "council"
    council.mkdir(parents=True)
    founder = repo / "coordination" / "founder"
    founder.mkdir(parents=True)
    security = repo / "coordination" / "security"
    security.mkdir(parents=True)

    # pointer + missing authority on active lock
    daemon = repo / "coordination" / "council" / "live_proof_packages" / "SOAK" / "daemon"
    daemon.mkdir(parents=True)
    ledger = daemon / "task_lease_ledger.jsonl"
    ledger.write_text(
        json.dumps({
            "ts": "2026-07-14T00:00:00Z",
            "task_id": "T-1",
            "lease_id": "lease-1",
            "status": "ACQUIRED",
        }) + "\n"
    )
    (council / "active_runtime_source.json").write_text(json.dumps({
        "scheduler_instance_id": "sched-test",
        "ledger_path": str(ledger),
        "evidence_dir": str(daemon),
        "pid": 1,
        "published_at": "2026-07-14T00:00:00Z",
    }))
    (leases / "T-1.abc.lock").write_text(json.dumps({
        "task_id": "T-1",
        "lease_id": "lease-1",
        "status": "ACTIVE",
        "lease_status": "RUNNING",
        "scheduler_instance_id": "sched-test",
        # deliberately no authority_decision_id
        "expires_at": "2099-01-01T00:00:00+00:00",
    }))
    (security / "helm_control_posture.json").write_text(json.dumps({
        "posture_percent": 95.0,
        "high_findings": 0,
    }))

    jspace = tmp_path / "jspace"
    result = run_hjos_cycle(repo_root=repo, ledger_root=jspace)
    assert result["state_mutated"] is False
    assert result["promotion_authority"] == "NONE"
    assert result["overall"] == "CONTRADICTED"
    assert result["recommended_action"] == "WITHHOLD_PROMOTION"

    assessments = JSpaceLedger(jspace).recent_assessments()
    subjects = {a["subject"] for a in assessments}
    assert "active_leases_authority" in subjects
    auth_rows = [a for a in assessments if a["subject"] == "active_leases_authority"]
    assert any(a["assessment"] == "CONTRADICTED" for a in auth_rows)
    health = json.loads((jspace / "health.json").read_text())
    assert health["promotion_authority"] == "NONE"
    assert health["state_mutated"] is False


def test_cycle_bound_lease_not_contradicted(tmp_path: Path):
    repo = tmp_path / "repo"
    leases = repo / "coordination" / "leases"
    leases.mkdir(parents=True)
    council = repo / "coordination" / "council"
    council.mkdir(parents=True)
    security = repo / "coordination" / "security"
    security.mkdir(parents=True)
    (repo / "coordination" / "founder").mkdir(parents=True)

    daemon = repo / "coordination" / "council" / "pkg" / "daemon"
    daemon.mkdir(parents=True)
    ledger = daemon / "task_lease_ledger.jsonl"
    ledger.write_text("")
    (council / "active_runtime_source.json").write_text(json.dumps({
        "scheduler_instance_id": "sched-ok",
        "ledger_path": str(ledger),
        "evidence_dir": str(daemon),
    }))
    (leases / "T-2.abc.lock").write_text(json.dumps({
        "task_id": "T-2",
        "lease_id": "lease-2",
        "status": "ACTIVE",
        "authority_decision_id": "AUTH-1",
        "scheduler_instance_id": "sched-ok",
        "expires_at": "2099-01-01T00:00:00+00:00",
    }))
    (security / "helm_control_posture.json").write_text(json.dumps({
        "posture_percent": 100.0,
        "high_findings": 0,
    }))

    jspace = tmp_path / "jspace2"
    result = run_hjos_cycle(repo_root=repo, ledger_root=jspace)
    assert result["state_mutated"] is False
    # Should not be CONTRADICTED on authority binding
    assessments = JSpaceLedger(jspace).recent_assessments()
    auth_rows = [a for a in assessments if a["subject"] == "active_leases_authority"]
    assert auth_rows
    assert all(a["assessment"] != "CONTRADICTED" for a in auth_rows)


def test_ledger_append_only(tmp_path: Path):
    led = JSpaceLedger(tmp_path)
    from backend.jspace.schema import JSpaceEvent
    led.append_event(JSpaceEvent(event_type="T", source="t", subject="s"))
    led.append_event(JSpaceEvent(event_type="T", source="t", subject="s2"))
    rows = led.read_jsonl(led.events_path)
    assert len(rows) == 2
