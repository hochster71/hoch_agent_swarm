"""HJOS false-red latch regression (SWARM-4).

Two specialist subjects could emit a red verdict (CONTRADICTED / BLOCKED) but had
NO branch that could ever emit a clearing verdict. Because the /brain view is
ledger-latest-per-(observer,subject), a transient red LATCHED forever — the stale
verdict never got superseded even after the condition resolved.

These tests assert the CONTRACT both ways:
  1. the clearing verdict is emitted when the condition is genuinely clear, AND
  2. detection is NOT weakened — the red verdict still fires when the condition holds.

Pure in-memory; no coordination/ tree, ledger, or network is touched.
"""
from __future__ import annotations

from backend.jspace.observers.flow_sentinel import FlowSentinel
from backend.jspace.observers.truth_sentinel import TruthSentinel
from backend.jspace.truth_classes import TruthAssessment

CID = "TEST-LATCH"


def _subj(result, subject):
    return [a for a in result.assessments if a.subject == subject]


# --------------------------------------------------------------- scheduler_instance_consistency
def test_scheduler_consistency_emits_clear_when_no_foreign_locks():
    """No lock references a foreign scheduler_instance_id -> an explicit CONFIRMED_LIVE
    all-clear must be emitted so the ledger-latest brain view can supersede a stale red."""
    snap = {"runtime": {
        "pointer": {"ledger_path": "x", "scheduler_instance_id": "sched-A"},
        "pointer_path": "coordination/council/active_runtime_source.json",
        "active_locks": [{"task_id": "T1", "status": "ACTIVE"}],  # unlabeled: not foreign
    }}
    got = _subj(TruthSentinel(CID).observe(snap), "scheduler_instance_consistency")
    assert len(got) == 1
    assert got[0].assessment == TruthAssessment.CONFIRMED_LIVE


def test_scheduler_consistency_still_contradicts_on_foreign_lock():
    """Detection preserved: a lock on a different scheduler_instance_id still fails closed."""
    snap = {"runtime": {
        "pointer": {"ledger_path": "x", "scheduler_instance_id": "sched-A"},
        "pointer_path": "coordination/council/active_runtime_source.json",
        "active_locks": [{"task_id": "T1", "status": "ACTIVE", "scheduler_instance_id": "sched-B"}],
    }}
    got = _subj(TruthSentinel(CID).observe(snap), "scheduler_instance_consistency")
    assert len(got) == 1
    assert got[0].assessment == TruthAssessment.CONTRADICTED


# ------------------------------------------------------------------------- concurrency_pressure
def test_concurrency_emits_clear_within_capacity():
    """<= 8 active locks -> an explicit CONFIRMED_LIVE all-clear must be emitted."""
    locks = [{"task_id": f"T{i}", "status": "ACTIVE"} for i in range(3)]
    snap = {"runtime": {"pointer": {"ledger_path": "x", "scheduler_instance_id": "s"},
                        "active_locks": locks}}
    got = _subj(FlowSentinel(CID).observe(snap), "concurrency_pressure")
    assert len(got) == 1
    assert got[0].assessment == TruthAssessment.CONFIRMED_LIVE


def test_concurrency_still_blocks_over_capacity():
    """Detection preserved: > 8 active locks still raises BLOCKED."""
    locks = [{"task_id": f"T{i}", "status": "ACTIVE"} for i in range(9)]
    snap = {"runtime": {"pointer": {"ledger_path": "x", "scheduler_instance_id": "s"},
                        "active_locks": locks}}
    got = _subj(FlowSentinel(CID).observe(snap), "concurrency_pressure")
    assert len(got) == 1
    assert got[0].assessment == TruthAssessment.BLOCKED
