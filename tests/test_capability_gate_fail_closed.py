"""Fail-closed dispatch-time capability gate — proves the Epic Fury lane-scope leak is fixed.

Sealed soak HELM-SOAK-24H-20260715T194547Z passed 19/20; the sole failure was
`epic_fury_stayed_lane_scoped=false`: over 1383 rounds the Epic Fury
APPLE_DISTRIBUTION task (required_capability=APP_STORE_CONNECT_OBSERVATION)
dispatched once (round 644) when the blocker register momentarily reported no
active Apple block, leaving the dynamically-derived `blocked_capabilities` empty.

The fix makes the gate DEFAULT-DENY: a task declaring a required_capability
dispatches ONLY if that capability is positively granted
(DISPATCH_GRANTED_CAPABILITIES). No blocker is required to hold the lock, so a
missing / resolved / parse-failed blocker register can no longer leak.

These tests drive the SAME dispatch path (PersistentScheduler.rank_tasks) that
run_once() uses, across MANY iterations and across EVERY blocker state, and
assert the EF task is blocked EVERY time (0 admissions).
"""
import tempfile
from pathlib import Path

import pytest

from backend.mission_control.persistent_scheduler import (
    PersistentScheduler,
    DISPATCH_GRANTED_CAPABILITIES,
)

EF_CAP = "APP_STORE_CONNECT_OBSERVATION"


def _scheduler():
    tmp = Path(tempfile.mkdtemp())
    sched = PersistentScheduler(evidence_dir=tmp)
    # Deterministic: point repo_root at an empty dir so no stray operator-hold /
    # blocker files influence the gate. The gate must hold on the tasks/blockers
    # we pass explicitly, independent of any on-disk state.
    sched.repo_root = tmp
    return sched


def _ef_task(n):
    return {"task_id": f"SOAK-EF-{n}", "mission_id": f"M-SOAK-EF-{n}",
            "target_pod": "HASF", "required_capability": EF_CAP,
            "step_index": 0, "dependencies": ""}


def _pod_task(pod, n):
    # Unrelated HASF (and other-factory) engineering work: no capability required.
    return {"task_id": f"SOAK-{pod}-{n}", "mission_id": f"M-SOAK-{pod}-{n}",
            "target_pod": pod, "required_capability": None,
            "step_index": 0, "dependencies": ""}


def _local_task(n):
    # Moonshot-style task: LOCAL_ONLY is positively granted and MUST dispatch.
    return {"task_id": f"T-MOON-{n}", "mission_id": f"M-MOON-{n}",
            "target_pod": "HASF", "required_capability": "LOCAL_ONLY",
            "step_index": 0, "dependencies": ""}


# Every blocker state that occurred (or could occur) during the soak — including
# the exact leak condition (no active Apple block) and the racy empty list.
BLOCKER_STATES = [
    [],                                                # parse-fail / missing register -> load_blockers()==[]
    [{"id": "G-6", "status": "RESOLVED"}],             # Apple review resolved
    [{"id": "G-7", "status": "PASS"}],                 # founder Apple account cleared
    [{"id": "G-6", "status": "RESOLVED"},
     {"id": "G-7", "status": "PASS"}],                 # both cleared -> epic_fury_blocked False (round-644 shape)
    [{"id": "G-6", "status": "PENDING"}],              # still blocked
    [{"id": "G-7", "status": "BLOCKED_FOUNDER_ACTION"}],
    [{"id": "G-0", "status": "RESOLVED"}],             # unrelated blockers only
]


def test_local_only_is_granted():
    assert "LOCAL_ONLY" in DISPATCH_GRANTED_CAPABILITIES
    assert EF_CAP not in DISPATCH_GRANTED_CAPABILITIES


def test_ef_blocked_every_cycle_5000_iterations():
    """Epic Fury APP_STORE_CONNECT_OBSERVATION task: 0 dispatches across 5000 cycles,
    cycling through EVERY blocker state (fully covers the round-644 leak state)."""
    sched = _scheduler()
    admitted = 0
    N = 5000
    for i in range(N):
        blockers = BLOCKER_STATES[i % len(BLOCKER_STATES)]
        tasks = [_ef_task(i), _pod_task("HASF", i), _pod_task("HRF", i)]
        ranked_ids = {t["task_id"] for t in sched.rank_tasks(tasks, blockers)}
        if f"SOAK-EF-{i}" in ranked_ids:
            admitted += 1
    assert admitted == 0, f"EF leaked {admitted}/{N} cycles — gate is NOT fail-closed"


def test_ef_denied_when_no_blocker_present_leak_condition():
    """The exact leak: NO active Apple blocker -> old gate had empty blocked_capabilities
    and admitted EF. Fail-closed gate must still DENY."""
    sched = _scheduler()
    for blockers in ([], [{"id": "G-6", "status": "RESOLVED"}, {"id": "G-7", "status": "PASS"}]):
        for i in range(500):
            ranked_ids = {t["task_id"] for t in sched.rank_tasks([_ef_task(i)], blockers)}
            assert f"SOAK-EF-{i}" not in ranked_ids


def test_unknown_capability_denied():
    """A capability the system has never heard of must be DENIED (default-deny)."""
    sched = _scheduler()
    t = {"task_id": "X-UNKNOWN", "mission_id": "M-X", "target_pod": "HASF",
         "required_capability": "SOME_FUTURE_UNGRANTED_CAP", "step_index": 0, "dependencies": ""}
    ranked_ids = {r["task_id"] for r in sched.rank_tasks([t], [])}
    assert "X-UNKNOWN" not in ranked_ids


def test_unrelated_hasf_work_continues():
    """Lane-scope invariant: capability-free HASF/other work is NOT withheld by the gate."""
    sched = _scheduler()
    for blockers in BLOCKER_STATES:
        tasks = [_pod_task("HASF", 1), _pod_task("HRF", 1), _pod_task("HCF", 1)]
        ranked_ids = {t["task_id"] for t in sched.rank_tasks(tasks, blockers)}
        assert "SOAK-HASF-1" in ranked_ids
        assert "SOAK-HRF-1" in ranked_ids
        assert "SOAK-HCF-1" in ranked_ids


def test_local_only_task_dispatches():
    """Positively-granted LOCAL_ONLY (moonshot) tasks must pass the gate under all states."""
    sched = _scheduler()
    for blockers in BLOCKER_STATES:
        ranked_ids = {t["task_id"] for t in sched.rank_tasks([_local_task(9)], blockers)}
        assert "T-MOON-9" in ranked_ids


def test_ef_and_local_mixed_batch():
    """Mixed batch: EF denied, LOCAL_ONLY + capability-free admitted — even with no blockers."""
    sched = _scheduler()
    tasks = [_ef_task(3), _local_task(3), _pod_task("HASF", 3)]
    ranked_ids = {t["task_id"] for t in sched.rank_tasks(tasks, [])}
    assert "SOAK-EF-3" not in ranked_ids
    assert "T-MOON-3" in ranked_ids
    assert "SOAK-HASF-3" in ranked_ids


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
