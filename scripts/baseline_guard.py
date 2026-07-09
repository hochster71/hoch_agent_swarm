#!/usr/bin/env python3
"""HOCH BASELINE GUARD — the ONE authority for "known good".

Why this exists: the repo accumulated ~71 drift/baseline/checksum/seal artifacts that
OBSERVE drift but never ENFORCE it, so the system kept cycling back. This replaces all of
them with a single git-anchored, fail-closed guard.

Principles:
  - git IS the checksum register. The baseline is a git tag; blob SHAs are immutable hashes.
  - Guard CODE + a few config INVARIANTS. Do NOT baseline churning runtime state (that is
    noise by design — gitignore it instead).
  - Fail closed. On drift: report exact deltas and exit non-zero. NEVER auto-launder.
  - Enforcement is opt-in and explicit: --revert snaps guarded CODE back to the baseline tag.
  - ONE guard, one cadence, last word. Not 71 observers.

Usage:
  python3 scripts/baseline_guard.py                 # check drift vs pinned baseline tag
  python3 scripts/baseline_guard.py --tag <gittag>  # check vs a specific tag
  python3 scripts/baseline_guard.py --revert        # snap guarded CODE back to baseline
  # pin the baseline:  git tag hoch-baseline-YYYYMMDD && echo it into baseline_tag.txt
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE_TAG_FILE = ROOT / "has_live_project_tracker/data/baseline_tag.txt"

# Small, meaningful set of CODE/config files whose drift actually matters. Extend deliberately
# — the value is a SHORT list everyone trusts, not an exhaustive one nobody reads.
GUARDED_PATHS = [
    "backend/model_gateway.py",
    "backend/cluster_manager.py",
    "scripts/ag_execution_runner.py",
    "scripts/ag_execution_daemon.py",
    "infra/hoch-200/vps/relay-api/app.py",
    "has_live_project_tracker/data/orchestration_bridge_control.json",
]


def sh(*args: str) -> str:
    return subprocess.run(args, capture_output=True, text=True, cwd=ROOT).stdout.strip()


def code_drift(tag: str) -> str:
    """Working-tree drift of guarded files vs the baseline tag (includes uncommitted)."""
    return sh("git", "diff", "--stat", tag, "--", *GUARDED_PATHS)


def invariants() -> dict:
    """A few runtime invariants that must hold regardless of who edited what.
    These are the things that kept silently regressing."""
    checks: dict[str, bool] = {}
    try:
        c = json.loads((ROOT / "has_live_project_tracker/data/orchestration_bridge_control.json").read_text())
        checks["execution_posture == DOORSTEP"] = c.get("execution_posture") == "DOORSTEP"
        # Baseline change approved by Michael Hoch 2026-07-09: council fully seated
        # (8 provider keys validated), revenue push active — provider calls now the
        # intended posture. See docs/audits/HELM_FULL_AUDIT_GAP_PERT_2026-07-08.md §6.
        checks["provider_api_calls ON (council live, approved 2026-07-09)"] = c.get("allow_provider_api_calls") is True
        checks["founder_gated_execution OFF"] = c.get("allow_founder_gated_execution") is False
    except Exception:
        checks["control_plane readable"] = False
    try:
        cm = (ROOT / "backend/cluster_manager.py").read_text()
        checks["no fabricated ACTIVITY_POOLS (fleet theater)"] = "ACTIVITY_POOLS = {" not in cm
    except Exception:
        checks["cluster_manager readable"] = False
    try:
        # North star is "complete AND monetize" — the PERT must model the founder-gated
        # revenue path, not just internal buildout, or "% to GOAL" is fake-green.
        ps = (ROOT / "backend/pert_server.py").read_text()
        checks["PERT models the revenue path (R1..R4), not just buildout"] = (
            '"phase": "REVENUE"' in ps and '"id": "R4"' in ps)
        # No fake-green magic numbers in the metrics summary — these must be derived.
        checks["PERT metrics derived (not hardcoded tests/evidence/accountability)"] = not any(
            lit in ps for lit in ('"tests_passing_count": 84',
                                  '"agent_accountability_score": 80.0',
                                  '"evidence_coverage_percent": 100,'))
    except Exception:
        checks["pert_server readable"] = False
    return checks


def runtime_invariants() -> dict:
    """Live control-plane invariants. Fail-soft: a check that can't run here (tool missing,
    or not on the control-plane host) is simply omitted, never a false FAIL. These catch the
    exact drift class we hit: an orphaned process shadowing a managed one, duplicate servers."""
    import shutil
    checks: dict[str, bool] = {}
    if shutil.which("lsof"):
        pids = [p for p in sh("lsof", "-tiTCP:8000", "-sTCP:LISTEN").split() if p.strip()]
        if pids:  # only assert if something is serving :8000
            checks[":8000 has a single listener (no orphan shadowing launchd)"] = (len(pids) == 1)
    if shutil.which("pgrep"):
        procs = [l for l in sh("pgrep", "-f", "ollama serve").splitlines() if l.strip()]
        checks["single ollama serve (no duplicate model server)"] = (len(procs) <= 1)

    # STALE-CODE / ORPHAN detection — the root cause of "it never stays". A service whose
    # listener process STARTED BEFORE the last commit to the file it serves is running old
    # code (an orphan that survived restarts). Catch it: process_start_epoch < file_commit_epoch.
    import datetime
    SERVICE_PORTS = {8000: "backend/main.py", 8765: "backend/pert_server.py"}
    if shutil.which("lsof") and shutil.which("ps"):
        for port, served_file in SERVICE_PORTS.items():
            pids = [p for p in sh("lsof", f"-tiTCP:{port}", "-sTCP:LISTEN").split() if p.strip()]
            if not pids:
                continue  # service not running on this host — skip (fail-soft)
            if len(pids) > 1:
                checks[f":{port} single listener (no orphan)"] = False
                continue
            checks[f":{port} single listener (no orphan)"] = True
            lstart = sh("ps", "-o", "lstart=", "-p", pids[0]).strip()
            ct = sh("git", "log", "-1", "--format=%ct", "--", served_file).strip()
            try:
                started = datetime.datetime.strptime(lstart, "%a %b %d %H:%M:%S %Y").timestamp()
                committed = int(ct)
                checks[f":{port} serving current code (not stale/orphan)"] = started >= committed
            except Exception:
                pass  # can't determine — don't false-FAIL
    return checks


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default=None, help="baseline git tag (default: pinned in baseline_tag.txt)")
    ap.add_argument("--revert", action="store_true", help="snap guarded CODE back to the baseline tag")
    ap.add_argument("--invariants-only", action="store_true",
                    help="check only runtime invariants (for the pre-commit change-board gate); "
                         "ignores normal in-progress code drift")
    args = ap.parse_args()

    if args.invariants_only:
        inv = invariants()
        fails = [k for k, v in inv.items() if not v]
        print("=== CHANGE-BOARD GATE (invariants) ===")
        for k, v in inv.items():
            print(f"  {'OK  ' if v else 'FAIL'} {k}")
        if fails:
            print("BLOCKED: commit would regress a baseline invariant: " + ", ".join(fails))
            sys.exit(1)
        print("APPROVED: invariants hold.")
        sys.exit(0)

    tag = args.tag or (BASELINE_TAG_FILE.read_text().strip() if BASELINE_TAG_FILE.exists() else "")
    if not tag:
        print("NO BASELINE PINNED. Set one:\n"
              "  git tag hoch-baseline-$(date -u +%Y%m%d)\n"
              f"  echo hoch-baseline-$(date -u +%Y%m%d) > {BASELINE_TAG_FILE}")
        sys.exit(2)
    if sh("git", "rev-parse", "-q", "--verify", f"refs/tags/{tag}") == "":
        print(f"BASELINE TAG '{tag}' does not exist. Create it: git tag {tag}")
        sys.exit(2)

    drift = code_drift(tag)
    inv = invariants()
    rt = runtime_invariants()
    all_inv = {**inv, **rt}
    inv_fail = [k for k, v in all_inv.items() if not v]
    verdict = "PASS" if (not drift and not inv_fail) else "DRIFT"

    print(f"=== BASELINE GUARD vs {tag}: {verdict} ===")
    print("-- guarded code drift --")
    print("  " + (drift.replace("\n", "\n  ") if drift else "(none — matches baseline)"))
    print("-- config invariants --")
    for k, v in inv.items():
        print(f"  {'OK  ' if v else 'FAIL'} {k}")
    print("-- runtime invariants --")
    for k, v in rt.items():
        print(f"  {'OK  ' if v else 'FAIL'} {k}")

    if args.revert and drift:
        for p in GUARDED_PATHS:
            sh("git", "checkout", tag, "--", p)
        print("-- reverted guarded CODE to baseline (runtime state left untouched) --")

    sys.exit(0 if verdict == "PASS" else 1)


if __name__ == "__main__":
    main()
