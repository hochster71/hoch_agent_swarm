#!/usr/bin/env python3
"""HELM CONTINUOUS FRESHNESS REFRESHER — keep COMPUTED truth sources inside budget.

WHY
---
``backend/runtime_freshness.py`` gives every HELM truth source a TIGHT per-signal
budget and honestly badges FRESH / STALE / UNKNOWN. That is the *scoreboard*. This
module is the *engine that keeps the score green* for the sources that are legitimately
re-derivable: it re-runs their real regenerators before their budgets expire, so the 14
UIs that read those files are always current — replacing the once-daily
``helm-runtime-tick`` as the thing that keeps data fresh.

DOCTRINE — what it may and may NOT touch (NO FAKE GREEN)
-------------------------------------------------------
It may ONLY re-run legitimate regenerators for COMPUTED / DERIVED sources:

    control_plane   -> scripts/build_control_plane_status.py   (rebuilds control_plane_status.json)
    goal_state      -> scripts/goal/goal_engine.py             (writes goal_state.json)
    mission_state   -> scripts/goal/goal_engine.py             (same run writes mission_state.json)

It MUST NOT fabricate or touch LIVENESS signals. The following are DELIBERATELY EXCLUDED
from the refresh registry — if their real producer is down they SHOULD read stale, and
the freshness board flags that honestly:

    supervisor_heartbeat   -- produced by the real supervisor; faking it == fake liveness
    runtime_truth_snapshot -- produced by the live soak; frozen soak SHOULD look stale
    orchestration_authority-- HOCH-200 authority, refreshed only by secure_sync (not local compute)
    helm_runtime_state     -- produced by the supervisor runtime loop; not a safe compute
    helm_agent_registry    -- factory registry has NO safe read-only regenerator here
                              (build_control_plane_status.py only READS it; its writers are
                               runtime dispatchers). Leave it; let the board flag it.

The refresher NEVER writes a truth file itself — it only invokes each source's own
regenerator subprocess. If a regenerator errors, we REPORT it and leave the file as-is;
we never paper over a failure. It also never restarts the daemon or disturbs the soak.

Safe to run during the live soak: the three regenerators are read-mostly compute
(goal_engine + build_control_plane were already run safely during the soak).

USAGE
-----
    python3 scripts/runtime_refresher.py --plan          # dry run: show what is due, run nothing
    python3 scripts/runtime_refresher.py --once          # run each DUE regenerator one time
    python3 scripts/runtime_refresher.py --loop           # launchd loop (default interval 300s)
    python3 scripts/runtime_refresher.py --loop --interval 300
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import runtime_freshness as rf  # noqa: E402


# ---------------------------------------------------------------------------
# REFRESH REGISTRY — refreshable COMPUTED signal -> its real regenerator command.
# min_interval_seconds is derived from the signal's budget in runtime_freshness.py
# (refresh at ~budget/3, so the source is re-derived well before it can expire).
# ---------------------------------------------------------------------------
def _interval_for(signal: str) -> int:
    """~budget/3, floored at 30s so we never busy-refresh a fast signal."""
    budget = int(rf.FRESHNESS_BUDGETS.get(signal, 0))
    return max(30, budget // 3) if budget else 300


REFRESH_REGISTRY: Dict[str, Dict[str, Any]] = {
    "control_plane": {
        "command": ["python3", "scripts/build_control_plane_status.py"],
        "min_interval_seconds": _interval_for("control_plane"),   # budget 120 -> 40s
        "regenerates": ["control_plane"],
        "why": "COMPUTED sidecar snapshot. build_control_plane_status.py rebuilds "
               "has_live_project_tracker/data/control_plane_status.json read-only from "
               "its source files. It only READS the liveness/authority sources.",
    },
    "goal_state": {
        "command": ["python3", "scripts/goal/goal_engine.py"],
        "min_interval_seconds": _interval_for("goal_state"),      # budget 3600 -> 1200s
        "regenerates": ["goal_state", "mission_state"],
        "why": "DERIVED goal metrics. goal_engine.py recomputes completion ONLY from "
               "validators that actually ran and writes coordination/goal/goal_state.json; "
               "the same run also writes coordination/goal/mission_state.json.",
    },
    "mission_state": {
        # Same regenerator as goal_state; deduped at run time so goal_engine runs once.
        "command": ["python3", "scripts/goal/goal_engine.py"],
        "min_interval_seconds": _interval_for("mission_state"),   # budget 3600 -> 1200s
        "regenerates": ["goal_state", "mission_state"],
        "why": "DERIVED executive mission view, written by the same goal_engine.py run "
               "that produces goal_state (dedup ensures a single subprocess).",
    },
}

# LIVENESS / non-regenerable signals we DELIBERATELY REFUSE to refresh. Kept as data so a
# guard test can assert none of these ever leak into REFRESH_REGISTRY. (NO FAKE GREEN.)
LIVENESS_EXCLUDED: Dict[str, str] = {
    "supervisor_heartbeat":
        "LIVENESS: must be produced by the real supervisor. Writing it would fake liveness.",
    "runtime_truth_snapshot":
        "LIVENESS: produced by the live soak. A frozen soak SHOULD read stale — honest.",
    "orchestration_authority":
        "HOCH-200 authority, refreshed only by secure_sync — not a safe local compute.",
    "helm_runtime_state":
        "Produced by the supervisor runtime loop; a refresher must not fabricate it.",
    "helm_agent_registry":
        "Factory registry has NO safe read-only regenerator here (build_control_plane_status.py "
        "only READS it; its writers are runtime dispatchers). Leave it; board flags it.",
}


# ---------------------------------------------------------------------------
# Scheduling / due logic (age-based, tied to the real freshness scoreboard)
# ---------------------------------------------------------------------------
def is_due(signal: str, *, root: Optional[Path] = None, now=None) -> Dict[str, Any]:
    """A refreshable signal is DUE when it is not currently comfortably fresh:

        - state != FRESH (STALE / UNKNOWN)                       -> due
        - age unknown (None)                                     -> due
        - age >= its min_interval (~budget/3)                    -> due (refresh before expiry)

    Ties dueness to the real observed freshness rather than a private clock, so the
    refresher is idempotent and never runs a source that is already comfortably fresh.
    """
    entry = REFRESH_REGISTRY[signal]
    interval = int(entry["min_interval_seconds"])
    ev = rf.evaluate_signal(signal, root=root, now=now)
    age = ev.get("age_seconds")
    state = ev.get("state")
    if state != "FRESH":
        due, reason = True, f"state={state} (not FRESH)"
    elif age is None:
        due, reason = True, "age unknown"
    elif age >= interval:
        due, reason = True, f"age {age:.0f}s >= interval {interval}s"
    else:
        due, reason = False, f"age {age:.0f}s < interval {interval}s"
    return {"signal": signal, "due": due, "reason": reason,
            "state": state, "age_seconds": age, "interval_seconds": interval}


def _fresh_line(signal: str, *, root: Optional[Path] = None) -> str:
    ev = rf.evaluate_signal(signal, root=root)
    age = "n/a" if ev.get("age_seconds") is None else f"{ev['age_seconds']:.0f}s"
    return f"{signal:22} {ev['state']:8} age={age:>9} / budget={ev['budget_seconds']}s"


def plan(*, root: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Read-only: evaluate dueness for every refreshable signal. Runs nothing."""
    return [is_due(sig, root=root) for sig in REFRESH_REGISTRY]


def run_once(*, root: Optional[Path] = None, dry_run: bool = False,
             timeout: int = 300) -> Dict[str, Any]:
    """Run each DUE regenerator once (deduped by command). Honest, fail-closed.

    Never writes a truth file directly — only invokes each source's regenerator. On
    failure it reports the error and leaves the file untouched (no fake refresh).
    """
    root = root or ROOT
    checks = plan(root=root)
    due_signals = [c["signal"] for c in checks if c["due"]]

    # Dedup commands: goal_state + mission_state share goal_engine.py -> one subprocess.
    cmd_to_signals: Dict[tuple, List[str]] = {}
    for sig in due_signals:
        cmd = tuple(REFRESH_REGISTRY[sig]["command"])
        cmd_to_signals.setdefault(cmd, []).append(sig)

    print("=" * 78)
    print(f"RUNTIME REFRESHER — {'PLAN (dry-run)' if dry_run else 'ONCE'}")
    print("=" * 78)
    print("BEFORE:")
    for sig in REFRESH_REGISTRY:
        print("  " + _fresh_line(sig, root=root))
    print("-" * 78)

    results: List[Dict[str, Any]] = []
    for cmd, signals in cmd_to_signals.items():
        label = "+".join(signals)
        if dry_run:
            print(f"WOULD RUN  {label:22} -> {' '.join(cmd)}")
            results.append({"signals": signals, "command": list(cmd),
                            "status": "WOULD_RUN", "returncode": None})
            continue
        print(f"RUN        {label:22} -> {' '.join(cmd)}")
        try:
            proc = subprocess.run(
                list(cmd), cwd=str(root), capture_output=True, text=True, timeout=timeout,
            )
        except Exception as e:  # noqa: BLE001 — report, never fake
            print(f"  FAILED (exec): {e}")
            results.append({"signals": signals, "command": list(cmd),
                            "status": "FAILED", "returncode": None, "error": str(e)})
            continue
        if proc.returncode == 0:
            print(f"  OK (rc=0)")
            results.append({"signals": signals, "command": list(cmd),
                            "status": "OK", "returncode": 0})
        else:
            tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-3:]
            print(f"  FAILED (rc={proc.returncode}) — file left as-is (honest):")
            for ln in tail:
                print(f"    {ln}")
            results.append({"signals": signals, "command": list(cmd),
                            "status": "FAILED", "returncode": proc.returncode,
                            "stderr_tail": tail})

    if not cmd_to_signals:
        print("(nothing due — all refreshable signals comfortably fresh)")

    print("-" * 78)
    print("AFTER:")
    for sig in REFRESH_REGISTRY:
        print("  " + _fresh_line(sig, root=root))
    print("=" * 78)

    ok = sum(1 for r in results if r["status"] in ("OK", "WOULD_RUN"))
    failed = sum(1 for r in results if r["status"] == "FAILED")
    return {"due": due_signals, "results": results, "ok": ok, "failed": failed}


def loop(interval: int = 300, *, root: Optional[Path] = None) -> int:
    """Idempotent launchd-friendly loop. Never restarts the daemon or touches the soak."""
    print(f"[runtime_refresher] loop start; interval={interval}s (Ctrl-C to stop)")
    while True:
        try:
            summary = run_once(root=root)
            if summary["failed"]:
                print(f"[runtime_refresher] {summary['failed']} regenerator(s) FAILED "
                      f"this pass — reported above, files left honest.")
        except Exception as e:  # noqa: BLE001 — a loop must survive one bad pass
            print(f"[runtime_refresher] pass error (continuing): {e}")
        time.sleep(max(30, interval))


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="HELM continuous freshness refresher")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--plan", action="store_true", help="dry-run: show what is due, run nothing")
    g.add_argument("--once", action="store_true", help="run each due regenerator one time")
    g.add_argument("--loop", action="store_true", help="loop forever (for launchd)")
    ap.add_argument("--interval", type=int, default=300, help="loop sleep seconds (default 300)")
    args = ap.parse_args(argv)

    if args.plan:
        run_once(dry_run=True)
        return 0
    if args.once:
        summary = run_once()
        # Exit non-zero if any regenerator failed, so callers/launchd logs surface it.
        return 1 if summary["failed"] else 0
    if args.loop:
        return loop(interval=args.interval)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
