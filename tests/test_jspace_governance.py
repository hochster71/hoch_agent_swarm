"""HJOS privilege-boundary governance tests (independent audit 2026-07-14).

These exist because Grok enabled automatic quarantine + orphan-lease hygiene on an
observer chartered read-only, self-authorized by a ~5-minute burn-in. These tests
prove the corrected boundary: mutation is fail-closed on a governance gate, the
truth schema differentiates observation vs containment mutation, and historical
findings survive containment (no self-clearing green).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from backend.jspace.burn_in import BurnInTracker
from backend.jspace.quarantine import (
    _governance,
    _mutation_authorized,
    execute_quarantine_if_allowed,
    quarantine_expired_orphan_locks,
)


def _write_gov(root: Path, **kw):
    d = {
        "automatic_quarantine_enabled": False,
        "orphan_lease_hygiene": "manual_approval",
        "authorizing_policy_id": None,
    }
    d.update(kw)
    (root / "coordination" / "jspace").mkdir(parents=True, exist_ok=True)
    (root / "coordination" / "jspace" / "quarantine_governance.json").write_text(
        json.dumps(d), encoding="utf-8"
    )


def _lease_dir(root: Path) -> Path:
    d = root / "coordination" / "leases"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write_lock(root: Path, task_id: str, *, expires: str, status="ACTIVE", instance=None):
    p = _lease_dir(root) / f"{task_id}.lock"
    p.write_text(json.dumps({
        "task_id": task_id, "lease_id": f"lease-{task_id}",
        "status": status, "expires_at": expires,
        "scheduler_instance_id": instance,
        "acquired_at": "2026-07-14T00:00:00+00:00",
    }), encoding="utf-8")
    return p


# ---------------------------------------------------------------- governance gate
def test_governance_denies_class_quarantine_without_policy(tmp_path):
    _write_gov(tmp_path, authorizing_policy_id=None, automatic_quarantine_enabled=True)
    logs = []
    r = execute_quarantine_if_allowed(
        enabled=True, reason="evidence_tampering", subject="x", evidence=[],
        cycle_id="C", observer="o", ledger_append=logs.append, repo_root=tmp_path,
    )
    assert r["executed"] is False
    assert r["blocked"] == "GOVERNANCE_DENY_NO_APPROVED_POLICY"


def test_governance_denies_orphan_hygiene_when_manual(tmp_path):
    _write_gov(tmp_path, orphan_lease_hygiene="manual_approval",
               authorizing_policy_id=None, automatic_quarantine_enabled=True)
    _write_lock(tmp_path, "SOAK-OLD", expires="2000-01-01T00:00:00+00:00")
    logs = []
    r = quarantine_expired_orphan_locks(
        enabled=True, current_instance_id="live", ledger_append=logs.append,
        repo_root=tmp_path, cycle_id="C",
    )
    assert r["executed"] is False
    assert r["blocked"] == "GOVERNANCE_DENY_ORPHAN_HYGIENE_MANUAL"
    # file NOT moved
    assert (_lease_dir(tmp_path) / "SOAK-OLD.lock").exists()


def test_unsupported_class_denied(tmp_path):
    _write_gov(tmp_path, authorizing_policy_id="POLICY-1", automatic_quarantine_enabled=True)
    logs = []
    r = execute_quarantine_if_allowed(
        enabled=True, reason="please_delete_everything", subject="x", evidence=[],
        cycle_id="C", observer="o", ledger_append=logs.append, repo_root=tmp_path,
    )
    assert r["executed"] is False
    assert r["blocked"] in ("CLASS_NOT_PERMITTED", "CHARTER_DENY")


def test_mutation_authorized_requires_policy_id():
    assert _mutation_authorized({"authorizing_policy_id": None,
                                 "automatic_quarantine_enabled": True},
                                kind="class_quarantine") is False
    assert _mutation_authorized({"authorizing_policy_id": "P",
                                 "automatic_quarantine_enabled": True},
                                kind="class_quarantine") is True
    # orphan hygiene needs explicit non-manual too
    assert _mutation_authorized({"authorizing_policy_id": "P",
                                 "automatic_quarantine_enabled": True,
                                 "orphan_lease_hygiene": "manual_approval"},
                                kind="orphan_hygiene") is False


# ---------------------------------------------------------------- classification
def test_live_instance_lock_spared(tmp_path):
    _write_gov(tmp_path, orphan_lease_hygiene="auto", authorizing_policy_id="P",
               automatic_quarantine_enabled=True)
    _write_lock(tmp_path, "LIVE", expires="2000-01-01T00:00:00+00:00", instance="live-1")
    logs = []
    quarantine_expired_orphan_locks(
        enabled=True, current_instance_id="live-1", ledger_append=logs.append,
        repo_root=tmp_path, cycle_id="C",
    )
    # belongs to current instance -> never moved even though expired
    assert (_lease_dir(tmp_path) / "LIVE.lock").exists()


def test_missing_authority_does_not_alone_prove_orphan(tmp_path):
    """A lock missing scheduler_instance_id but NOT expired must not be moved."""
    _write_gov(tmp_path, orphan_lease_hygiene="auto", authorizing_policy_id="P",
               automatic_quarantine_enabled=True)
    future = "2099-01-01T00:00:00+00:00"
    _write_lock(tmp_path, "FUTURE", expires=future, instance=None)
    logs = []
    r = quarantine_expired_orphan_locks(
        enabled=True, current_instance_id="live", ledger_append=logs.append,
        repo_root=tmp_path, cycle_id="C",
    )
    assert (_lease_dir(tmp_path) / "FUTURE.lock").exists()
    assert r["moved"] == []


def test_authorized_orphan_move_is_reversible_and_preserves_provenance(tmp_path):
    _write_gov(tmp_path, orphan_lease_hygiene="auto", authorizing_policy_id="P",
               automatic_quarantine_enabled=True)
    _write_lock(tmp_path, "SOAK-DEAD", expires="2000-01-01T00:00:00+00:00", instance=None)
    logs = []
    r = quarantine_expired_orphan_locks(
        enabled=True, current_instance_id="live", ledger_append=logs.append,
        repo_root=tmp_path, cycle_id="C",
    )
    assert r["executed"] is True
    # original gone from active dir, but preserved in quarantine (moved, not deleted)
    assert not (_lease_dir(tmp_path) / "SOAK-DEAD.lock").exists()
    qdirs = list((_lease_dir(tmp_path)).glob("_quarantine_hjos_orphans_*"))
    assert qdirs and (qdirs[0] / "SOAK-DEAD.lock").exists()
    preserved = json.loads((qdirs[0] / "SOAK-DEAD.lock").read_text())
    assert preserved["task_id"] == "SOAK-DEAD"  # provenance intact


# ---------------------------------------------------------------- burn-in honesty
def test_clean_cycle_requires_confirmed_live(tmp_path):
    b = BurnInTracker(tmp_path, min_cycles=3)
    st = b.record_cycle(cycle_id="C1", overall="CONTRADICTED", state_mutated=False, exception=None)
    assert st["clean_cycles"] == 0  # a CONTRADICTED cycle is NOT clean


def test_audit_disabled_burnin_stays_disabled(tmp_path):
    b = BurnInTracker(tmp_path, min_cycles=1)
    # pre-seed disabled_by_audit
    b.path.write_text(json.dumps({
        "min_cycles": 1, "completed_cycles": 9, "clean_cycles": 9,
        "burn_in_complete": False, "automatic_quarantine_enabled": False,
        "disabled_by_audit": True, "history": [],
    }), encoding="utf-8")
    st = b.record_cycle(cycle_id="C", overall="CONFIRMED_LIVE", state_mutated=False, exception=None)
    assert st["burn_in_complete"] is False
    assert st["automatic_quarantine_enabled"] is False


# ---------------------------------------------------------------- no self-clearing
def test_historical_findings_survive_when_active_zero(tmp_path):
    """Immutable ledger keeps CONTRADICTED history even with zero active alerts."""
    from backend.jspace.runner import _finding_history
    j = tmp_path / "coordination" / "jspace"
    j.mkdir(parents=True, exist_ok=True)
    (j / "assessments.jsonl").write_text(
        json.dumps({"observer": "o", "subject": "s", "assessment": "CONTRADICTED",
                    "observed_at": "t1"}) + "\n", encoding="utf-8")
    (j / "quarantine_requests.jsonl").write_text("", encoding="utf-8")
    h = _finding_history(j)
    assert h["historical_findings"] == 1
    assert h["unresolved_findings"] == 1  # nonzero even though no active alert


def test_flat_state_mutated_absent_from_cycle_result(tmp_path):
    """A cycle result must not carry a flat state_mutated:false; it carries
    differentiated mutation_truth instead."""
    from backend.jspace.runner import run_hjos_cycle
    r = run_hjos_cycle(repo_root=Path("."))
    assert "state_mutated" not in r  # flat lie removed
    assert "mutation_truth" in r
    assert set(r["mutation_truth"]) >= {
        "observation_state_mutated", "containment_state_mutated",
        "authoritative_state_mutated", "containment_authorized",
        "containment_policy_id", "containment_evidence",
    }
