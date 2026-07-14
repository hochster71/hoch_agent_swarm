"""WORK PACKAGE A — permanent regression guard.

The decisive defect: release_lease() failed, the scheduler discarded the result, and the
ledger recorded RELEASED anyway. "0 leaked leases" was measured by an instrument that could
not record a failure. These tests make that class of lie structurally impossible.
"""
import re, tempfile
from pathlib import Path

from backend.mission_control.per_task_lease import PerTaskLeaseManager

SCHED = Path("backend/mission_control/persistent_scheduler.py")


def test_failed_release_returns_false_and_does_not_unlink():
    lm = PerTaskLeaseManager(Path(tempfile.mkdtemp()))
    lease = lm.acquire_lease("T1", holder="test")
    assert lease
    assert lm.release_lease("T1", "lease-WRONG") is False   # cannot claim success
    assert lm._path("T1").exists()                          # did not unlink a foreign lock
    assert lm.release_lease("T1", lease["lease_id"]) is True
    assert not lm._path("T1").exists()


def test_no_release_site_bypasses_the_honest_wrapper():
    src = SCHED.read_text()
    raw = re.findall(r"self\.lease_manager\.release_lease\([^)]*\)", src)
    assert len(raw) == 1, f"{len(raw)} raw release sites bypass _release_lease_logged"
    assert src.count("self._release_lease_logged(") >= 6


def test_ledger_status_cannot_be_released_without_lock_removal():
    src = SCHED.read_text()
    assert '"status": status_if_ok if ok else "RELEASE_FAILED"' in src
    assert '"lock_file_removed": ok' in src
    # and the mismatch path must log RELEASE_FAILED, never RELEASED
    assert '"status": "RELEASE_FAILED"' in src
