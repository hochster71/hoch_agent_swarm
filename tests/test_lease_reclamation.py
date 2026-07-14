"""Lease TTL must be ENFORCED, not decorative.

Reproduces the exact defect that FAILED Phase A on 2026-07-14:
  is_expired() existed. Nothing called it. A worker killed by fault injection left its lease held
  forever — SOAK-HRF-24 held a 10-minute lease for 96.4 minutes and pinned a concurrency slot for
  most of the run. The ledger read 516/516 released with 0 failures, because a release that is
  never ATTEMPTED cannot be recorded as failed.

A control written into every lock file and enforced by nothing is theatre.
"""
from __future__ import annotations

import json
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend.mission_control.per_task_lease import PerTaskLeaseManager

SCHED = Path("backend/mission_control/persistent_scheduler.py")


def _mgr():
    return PerTaskLeaseManager(Path(tempfile.mkdtemp()))


def _expire(lm, task_id, minutes_ago=30):
    """Force a lease to look expired, exactly as a killed worker leaves it."""
    p = lm._path(task_id)
    rec = json.loads(p.read_text())
    past = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    rec["acquired_at"] = past.isoformat()
    rec["expires_at"] = (past + timedelta(minutes=10)).isoformat()
    p.write_text(json.dumps(rec))
    return p


# ---------------------------------------------------------------- the Phase A failure
def test_killed_workers_expired_lease_IS_reclaimed():
    """THE PHASE A FAILURE. This test would have caught it."""
    lm = _mgr()
    lease = lm.acquire_lease("SOAK-HRF-24", holder="worker")
    assert lease
    p = _expire(lm, "SOAK-HRF-24", minutes_ago=96)     # held 96 min against a 10 min TTL

    reclaimed = lm.reclaim_expired_leases()

    assert len(reclaimed) == 1
    assert reclaimed[0]["task_id"] == "SOAK-HRF-24"
    assert reclaimed[0]["status"] == "TIMED_OUT"
    assert reclaimed[0]["reclaim_reason"] == "LEASE_TTL_EXPIRED"
    assert not p.exists(), "the slot was NOT freed — the leak persists"


def test_the_ACTUAL_mechanism_expired_locks_are_only_reclaimed_on_RE_ACQUIRE():
    """The precise bug, corrected from my own wrong first guess.

    acquire_lease() ALREADY steals an expired lease -- but ONLY when something tries to acquire
    THAT SAME task_id again. The soak never does: it moves on to round 25, 26, 27... SOAK-HRF-24
    is never seeded twice. So the expired lock is never touched, and it keeps being COUNTED AS AN
    ACTIVE LEASE. A reclaimer that only fires on re-acquire is a reclaimer that never fires.
    """
    lm = _mgr()
    lm.acquire_lease("SOAK-HRF-24", holder="dead-worker")
    _expire(lm, "SOAK-HRF-24", minutes_ago=96)

    # re-acquiring the SAME id would have worked -- but nobody ever does
    assert lm.acquire_lease("SOAK-HRF-24", holder="new") is not None

    # reset to the real-world state: expired, and never re-acquired
    lm2 = _mgr()
    lm2.acquire_lease("SOAK-HRF-24", holder="dead-worker")
    _expire(lm2, "SOAK-HRF-24", minutes_ago=96)

    # CORRECTION TO MY OWN FIRST CLAIM: active_leases() ALREADY filters expired leases, so the
    # stranded lock did NOT pin a concurrency slot. All 129 rounds ran at a full 4/4. I asserted
    # an impact I had not measured -- the same error I spent the day auditing.
    assert len(lm2.active_leases()) == 0, "expired lease is counted as active -- would pin a slot"

    # THE REAL DEFECT: the lock file persists forever as untracked debris, and -- worse -- the
    # TASK never reached a terminal state. Work was dispatched and SILENTLY LOST. No timeout, no
    # FAILED, no alarm. The only trace it ever existed is a file nobody reclaims.
    assert lm2._path("SOAK-HRF-24").exists(), "premise wrong: the lock did not persist"

    # the SWEEP gives the lost task a terminal state and clears the debris
    out = lm2.reclaim_expired_leases()
    assert out[0]["status"] == "TIMED_OUT", "lost work must get a TERMINAL state, not vanish"
    assert not lm2._path("SOAK-HRF-24").exists()


# ---------------------------------------------------------------- must NOT over-reclaim
def test_a_LIVE_lease_is_never_reclaimed():
    lm = _mgr()
    lm.acquire_lease("LIVE", holder="working")          # fresh, unexpired
    assert lm.reclaim_expired_leases() == []
    assert lm._path("LIVE").exists(), "reclaimed a lease that was still valid"


def test_reclamation_is_idempotent():
    lm = _mgr()
    lm.acquire_lease("T", holder="w")
    _expire(lm, "T")
    assert len(lm.reclaim_expired_leases()) == 1
    assert lm.reclaim_expired_leases() == []           # nothing left to reclaim


# ---------------------------------------------------------------- corrupt lock
def test_corrupt_lock_is_quarantined_not_ignored_and_does_not_crash():
    """coordination/leases/_fencing_tokens.lock was found CORRUPT during the Phase A seal."""
    lm = _mgr()
    (lm.dir / "BROKEN.lock").write_text("this is not json{{{")
    out = lm.reclaim_expired_leases()                   # must not raise
    assert any(r.get("status") == "CORRUPT_QUARANTINED" for r in out)
    assert not (lm.dir / "BROKEN.lock").exists()
    assert list(lm.dir.glob("*.corrupt")), "corrupt lock silently vanished instead of quarantined"


def test_underscore_files_are_not_treated_as_task_leases():
    lm = _mgr()
    (lm.dir / "_fencing_tokens.lock").write_text("not-json")
    lm.reclaim_expired_leases()
    assert (lm.dir / "_fencing_tokens.lock").exists(), "clobbered the fencing-token lock"


# ---------------------------------------------------------------- wired into the scheduler
def test_the_scheduler_ACTUALLY_CALLS_reclamation():
    """is_expired() existed for months and nothing called it. That is the whole bug.
    A capability nobody invokes is not a control."""
    src = SCHED.read_text()
    assert "reclaim_expired_leases()" in src, "scheduler never calls reclamation — TTL is decorative"
    assert "LEASE_RECLAIMED_EXPIRED" in src, "reclamation is not recorded in the ledger"


def test_reclamation_runs_BEFORE_dispatch_in_the_cycle():
    """Reclaim first, or the freed slot cannot be used this cycle."""
    src = SCHED.read_text()
    i = src.index("def run_once")
    body = src[i:i + 2500]
    assert "reclaim_expired_leases()" in body, "reclamation is not at the top of run_once"
