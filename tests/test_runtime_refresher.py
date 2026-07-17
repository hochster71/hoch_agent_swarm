"""Tests for scripts/runtime_refresher.py — the continuous freshness refresher.

Covers:
  * schedule / due logic (FRESH-within-interval -> not due; stale/unknown/old -> due)
  * GUARD: liveness signals are NOT in the refresh registry (NO FAKE GREEN)
  * a failing regenerator is REPORTED, not faked (no file write, honest status)

All heavy regenerators are mocked — no real subprocess and no real state files.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

rr = importlib.import_module("scripts.runtime_refresher")


# ---------------------------------------------------------------------------
# GUARD: liveness signals must never leak into the refresh registry.
# ---------------------------------------------------------------------------
LIVENESS_SIGNALS = {
    "supervisor_heartbeat",
    "runtime_truth_snapshot",
    "orchestration_authority",
    "helm_runtime_state",
    "helm_agent_registry",
}


def test_liveness_signals_excluded_from_registry():
    for sig in LIVENESS_SIGNALS:
        assert sig not in rr.REFRESH_REGISTRY, (
            f"{sig} is a liveness/non-regenerable signal and must NOT be refreshable"
        )


def test_heartbeat_and_runtime_truth_specifically_excluded():
    # Explicit assertion the two most dangerous fakes are refused.
    assert "supervisor_heartbeat" not in rr.REFRESH_REGISTRY
    assert "runtime_truth_snapshot" not in rr.REFRESH_REGISTRY
    # And they are documented as deliberately excluded.
    assert "supervisor_heartbeat" in rr.LIVENESS_EXCLUDED
    assert "runtime_truth_snapshot" in rr.LIVENESS_EXCLUDED


def test_registry_only_contains_computed_signals():
    assert set(rr.REFRESH_REGISTRY) == {"control_plane", "goal_state", "mission_state"}
    # None of the refreshable signals overlap the excluded liveness set.
    assert set(rr.REFRESH_REGISTRY).isdisjoint(LIVENESS_SIGNALS)


def test_registry_and_excluded_are_disjoint():
    assert set(rr.REFRESH_REGISTRY).isdisjoint(set(rr.LIVENESS_EXCLUDED))


# ---------------------------------------------------------------------------
# Intervals derive from budgets (~budget/3).
# ---------------------------------------------------------------------------
def test_intervals_derived_from_budget_over_three():
    assert rr.REFRESH_REGISTRY["control_plane"]["min_interval_seconds"] == 120 // 3
    assert rr.REFRESH_REGISTRY["goal_state"]["min_interval_seconds"] == 3600 // 3
    assert rr.REFRESH_REGISTRY["mission_state"]["min_interval_seconds"] == 3600 // 3


# ---------------------------------------------------------------------------
# Due logic.
# ---------------------------------------------------------------------------
def _patch_eval(monkeypatch, table):
    """Patch rf.evaluate_signal to return canned freshness per signal."""
    def fake_eval(name, spec=None, *, root=None, now=None):
        state, age = table[name]
        return {"name": name, "state": state, "age_seconds": age,
                "budget_seconds": rr.rf.FRESHNESS_BUDGETS.get(name, 0)}
    monkeypatch.setattr(rr.rf, "evaluate_signal", fake_eval)


def test_fresh_within_interval_is_not_due(monkeypatch):
    # control_plane interval is 40s; age 10s and FRESH -> not due.
    _patch_eval(monkeypatch, {"control_plane": ("FRESH", 10.0)})
    d = rr.is_due("control_plane")
    assert d["due"] is False


def test_fresh_but_older_than_interval_is_due(monkeypatch):
    # FRESH but age 50s >= 40s interval -> refresh before it can expire.
    _patch_eval(monkeypatch, {"control_plane": ("FRESH", 50.0)})
    d = rr.is_due("control_plane")
    assert d["due"] is True
    assert "interval" in d["reason"]


def test_stale_signal_is_due(monkeypatch):
    _patch_eval(monkeypatch, {"goal_state": ("STALE", 99999.0)})
    assert rr.is_due("goal_state")["due"] is True


def test_unknown_signal_is_due(monkeypatch):
    _patch_eval(monkeypatch, {"mission_state": ("UNKNOWN", None)})
    d = rr.is_due("mission_state")
    assert d["due"] is True


# ---------------------------------------------------------------------------
# run_once: dedup + failing regenerator is reported, not faked.
# ---------------------------------------------------------------------------
class _Proc:
    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_goal_and_mission_dedup_to_single_subprocess(monkeypatch):
    # Both goal_state and mission_state due; they share goal_engine.py -> ONE run.
    _patch_eval(monkeypatch, {
        "control_plane": ("FRESH", 1.0),        # not due
        "goal_state": ("STALE", 5000.0),        # due
        "mission_state": ("STALE", 5000.0),     # due (same command)
    })
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return _Proc(0)
    monkeypatch.setattr(rr.subprocess, "run", fake_run)

    summary = rr.run_once()
    assert len(calls) == 1  # deduped
    assert calls[0][-1].endswith("goal_engine.py")
    assert summary["failed"] == 0


def test_failing_regenerator_reported_not_faked(monkeypatch, capsys):
    _patch_eval(monkeypatch, {
        "control_plane": ("UNKNOWN", None),     # due
        "goal_state": ("FRESH", 1.0),           # not due
        "mission_state": ("FRESH", 1.0),        # not due
    })

    def fake_run(cmd, **kwargs):
        return _Proc(1, stderr="boom: could not build control plane")
    monkeypatch.setattr(rr.subprocess, "run", fake_run)

    summary = rr.run_once()
    assert summary["failed"] == 1
    assert summary["ok"] == 0
    res = summary["results"][0]
    assert res["status"] == "FAILED"
    assert res["returncode"] == 1
    out = capsys.readouterr().out
    assert "FAILED" in out
    assert "left as-is" in out  # honest: file not faked


def test_exec_exception_is_reported_not_raised(monkeypatch):
    _patch_eval(monkeypatch, {
        "control_plane": ("UNKNOWN", None),
        "goal_state": ("FRESH", 1.0),
        "mission_state": ("FRESH", 1.0),
    })

    def boom(cmd, **kwargs):
        raise OSError("python3 not found")
    monkeypatch.setattr(rr.subprocess, "run", boom)

    summary = rr.run_once()  # must not raise
    assert summary["failed"] == 1
    assert summary["results"][0]["status"] == "FAILED"


def test_nothing_due_runs_no_subprocess(monkeypatch):
    _patch_eval(monkeypatch, {
        "control_plane": ("FRESH", 1.0),
        "goal_state": ("FRESH", 1.0),
        "mission_state": ("FRESH", 1.0),
    })
    calls = []
    monkeypatch.setattr(rr.subprocess, "run",
                        lambda cmd, **kw: calls.append(cmd) or _Proc(0))
    summary = rr.run_once()
    assert calls == []
    assert summary["due"] == []


def test_plan_dry_run_runs_no_subprocess(monkeypatch):
    _patch_eval(monkeypatch, {
        "control_plane": ("STALE", 9999.0),
        "goal_state": ("STALE", 9999.0),
        "mission_state": ("STALE", 9999.0),
    })
    called = {"n": 0}

    def fake_run(cmd, **kw):
        called["n"] += 1
        return _Proc(0)
    monkeypatch.setattr(rr.subprocess, "run", fake_run)

    summary = rr.run_once(dry_run=True)
    assert called["n"] == 0  # dry-run runs nothing
    assert all(r["status"] == "WOULD_RUN" for r in summary["results"])


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
