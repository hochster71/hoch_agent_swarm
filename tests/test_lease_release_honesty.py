"""Invariant: ledger must not record RELEASED unless lock file was removed."""
from __future__ import annotations

import json
from pathlib import Path

from backend.mission_control.per_task_lease import PerTaskLeaseManager
from backend.mission_control.persistent_scheduler import PersistentScheduler


def test_release_lease_false_when_missing(tmp_path: Path):
    mgr = PerTaskLeaseManager(lease_dir=tmp_path / "leases")
    assert mgr.release_lease("T-NONE", "lease-x") is False


def test_scheduler_never_logs_released_on_failed_release(tmp_path: Path):
    evid = tmp_path / "evid"
    evid.mkdir()
    sched = PersistentScheduler(evidence_dir=evid, publish_runtime_source=False)
    mgr = PerTaskLeaseManager(lease_dir=tmp_path / "leases")
    sched.lease_manager = mgr

    # Lock exists under different lease_id → release must fail, file remains
    lock = mgr._path("T-1")
    lock.write_text(json.dumps({
        "task_id": "T-1",
        "lease_id": "lease-OTHER",
        "status": "ACTIVE",
    }))

    ok = sched._release_lease_logged("T-1", "lease-WANTED", reason="test")
    assert ok is False
    assert lock.exists(), "failed release must not remove foreign/mismatched lock"

    rows = [
        json.loads(l)
        for l in (evid / "task_lease_ledger.jsonl").read_text().splitlines()
        if l.strip()
    ]
    assert rows, "must log the failed release"
    assert all(r.get("status") != "RELEASED" for r in rows)
    assert any(r.get("status") == "RELEASE_FAILED" for r in rows)
    assert any(r.get("lock_file_removed") is False for r in rows)


def test_successful_release_logs_released_and_removes_lock(tmp_path: Path):
    evid = tmp_path / "evid"
    evid.mkdir()
    sched = PersistentScheduler(evidence_dir=evid, publish_runtime_source=False)
    mgr = PerTaskLeaseManager(lease_dir=tmp_path / "leases")
    sched.lease_manager = mgr
    lock = mgr._path("T-2")
    lock.write_text(json.dumps({
        "task_id": "T-2",
        "lease_id": "lease-ok",
        "status": "ACTIVE",
    }))
    ok = sched._release_lease_logged("T-2", "lease-ok", reason="test_ok")
    assert ok is True
    assert not lock.exists()
    rows = [
        json.loads(l)
        for l in (evid / "task_lease_ledger.jsonl").read_text().splitlines()
        if l.strip()
    ]
    assert any(r.get("status") == "RELEASED" and r.get("lock_file_removed") is True for r in rows)


def test_already_released_does_not_invent_released_row(tmp_path: Path):
    evid = tmp_path / "evid"
    evid.mkdir()
    sched = PersistentScheduler(evidence_dir=evid, publish_runtime_source=False)
    mgr = PerTaskLeaseManager(lease_dir=tmp_path / "leases")
    sched.lease_manager = mgr
    # no lock file
    ok = sched._release_lease_logged("T-gone", "lease-x", reason="idempotent")
    assert ok is True
    ledger = evid / "task_lease_ledger.jsonl"
    assert not ledger.exists() or not ledger.read_text().strip()
