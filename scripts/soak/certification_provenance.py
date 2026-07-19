#!/usr/bin/env python3
"""certification_provenance.py — reproducibility + resource-trend reporting for a soak run.

READ-ONLY. Imports nothing from the running soak and mutates no soak state. Safe to
run against a live certification: it only reads `coordination/soak/*` and `git`.

WHY THIS IS SEPARATE FROM run_soak.py
-------------------------------------
Reproducibility is a SECOND dimension of a certification, orthogonal to runtime
correctness. A system can behave perfectly while producing evidence that cannot be
reproduced, because the source tree moved underneath it. Keeping the two apart means
a reproducibility problem never masquerades as a behavior problem, or vice versa.

This lives in its own module rather than inside the report generator so it can be
added while a certification is already running. Integrating it into
`run_soak.py`'s final report is deliberately deferred until the active run finishes —
editing a report generator mid-certification risks the evidence the run exists to
produce.

Emits the founder-specified block:

    Certification:
      runtime_observed: PASS|FAIL
      evidence_complete: PASS|FAIL
      reproducibility:
        commit_frozen: bool
        dirty_tree: bool
        head_changed: bool
        reproducibility_grade: OBSERVED|DERIVED|ASSERTED|UNKNOWN

The grade uses the founder-ratified truth vocabulary (proof_contract.Truth) — it does
not invent a parallel scale.

Usage:
    python3 scripts/soak/certification_provenance.py [--run-dir coordination/soak] [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
from typing import Any, Dict, List, Optional

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from backend.helm_runtime.mission_contract import (  # noqa: E402
    UNKNOWN_VALUE,
    capture_execution_context,
    reproducibility,
)


def _git(*args: str) -> Optional[str]:
    try:
        p = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=15)
        return p.stdout.strip() if p.returncode == 0 else None
    except Exception:
        return None


def head_changed_since(start_ts: str) -> Dict[str, Any]:
    """Did HEAD move after the run started? Derived from git log, not assumed."""
    if not start_ts or start_ts == UNKNOWN_VALUE:
        return {"changed": UNKNOWN_VALUE, "commits_during_run": []}
    out = _git("log", f"--since={start_ts}", "--pretty=%H %cI %s")
    if out is None:
        return {"changed": UNKNOWN_VALUE, "commits_during_run": []}
    commits = [l for l in out.splitlines() if l.strip()]
    return {"changed": bool(commits), "commits_during_run": commits}


def load_metrics(run_dir: str) -> List[Dict[str, Any]]:
    p = os.path.join(ROOT, run_dir, "soak_metrics.jsonl")
    if not os.path.exists(p):
        return []
    rows = []
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # a partially-flushed final line during a live run
    return rows


def resource_trend(rows: List[Dict[str, Any]], width_s: int = 600) -> List[Dict[str, Any]]:
    """Bucket resource metrics into windows so a TREND is visible, not a snapshot.

    A single high memory reading is ambiguous. A series distinguishes a leak (monotonic
    climb) from a plateau (high but stable) — different risks, different responses.
    """
    buckets: Dict[int, List[Dict[str, Any]]] = {}
    for r in rows:
        b = int(float(r.get("uptime_s", 0)) // width_s)
        buckets.setdefault(b, []).append(r)

    out = []
    for b, rs in sorted(buckets.items()):
        mem = [x["resources"]["system_mem_pct"] for x in rs
               if x.get("resources", {}).get("system_mem_pct") is not None]
        rss = [x["resources"]["daemon_rss_mb"] for x in rs
               if x.get("resources", {}).get("daemon_rss_mb") is not None]
        wal = [x["resources"]["wal_mb"] for x in rs
               if x.get("resources", {}).get("wal_mb") is not None]
        last_rt = rs[-1].get("runtime", {})
        out.append({
            "window": f"{b * width_s // 60}-{(b + 1) * width_s // 60}min",
            "sys_mem_pct_mean": round(statistics.mean(mem), 1) if mem else None,
            "sys_mem_pct_max": round(max(mem), 1) if mem else None,
            "daemon_rss_mb_max": round(max(rss), 1) if rss else None,
            "wal_mb": round(wal[-1], 2) if wal else None,
            "queue_depth": last_rt.get("queue_depth"),
            "completed": last_rt.get("completed_total"),
            "failed": last_rt.get("failed_total"),
            "p95_latency_s": last_rt.get("p95_mission_latency_s"),
        })
    return out


def classify_memory(trend: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Leak vs plateau, decided on the FLOOR rather than the mean.

    A half-mean or regression slope is phase-sensitive: an alternating sawtooth that
    happens to end on a peak reads as monotonic growth. That is how the first version
    of this function misclassified a clean oscillation as RISING.

    The robust signal for accumulation is whether the *floor* rises. A sawtooth
    returns to its baseline between spikes; a leak never gives the baseline back. So:
    compare the MINIMUM of the first half against the minimum of the second half.
    """
    means = [w["sys_mem_pct_mean"] for w in trend if w["sys_mem_pct_mean"] is not None]
    if len(means) < 3:
        return {"pattern": "INSUFFICIENT_DATA", "windows": len(means)}

    half = len(means) // 2
    floor_first, floor_second = min(means[:half]), min(means[half:])
    floor_drift = floor_second - floor_first
    mean_drift = statistics.mean(means[half:]) - statistics.mean(means[:half])
    spread = max(means) - min(means)

    if floor_drift >= 2.0:
        pattern = "RISING"
    elif spread <= 5.0:
        pattern = "PLATEAU"
    else:
        pattern = "OSCILLATING"

    return {
        "pattern": pattern,
        "floor_first_half": round(floor_first, 1),
        "floor_second_half": round(floor_second, 1),
        "floor_drift_pts": round(floor_drift, 1),
        "drift_pts": round(mean_drift, 1),
        "spread_pts": round(spread, 1),
        "latest": means[-1],
        "note": {
            "RISING": "the floor is climbing — consistent with accumulation; the run may not survive its full window",
            "PLATEAU": "high but stable — the run is not the thing growing; risk is ambient headroom, not accumulation",
            "OSCILLATING": "spikes without a rising floor — transient workers returning memory between missions",
        }[pattern],
    }


def build(run_dir: str = "coordination/soak") -> Dict[str, Any]:
    meta_p = os.path.join(ROOT, run_dir, "run_meta.json")
    meta = json.load(open(meta_p, encoding="utf-8")) if os.path.exists(meta_p) else {}
    snap_p = os.path.join(ROOT, run_dir, "soak_snapshot.json")
    snap = json.load(open(snap_p, encoding="utf-8")) if os.path.exists(snap_p) else {}

    ctx = capture_execution_context(ROOT)
    repro = reproducibility(ctx)
    head = head_changed_since(meta.get("start_ts", ""))

    rows = load_metrics(run_dir)
    trend = resource_trend(rows)
    mem = classify_memory(trend)

    rt = snap.get("runtime", {})
    gov = snap.get("governance", {})
    completed = rt.get("completed_total") or 0
    artifacts = gov.get("evidence_artifacts") or 0

    commit_frozen = head["changed"] is False
    dirty = ctx.get("dirty")

    if commit_frozen and dirty is False:
        grade = "OBSERVED"
    elif dirty is True or head["changed"] is True:
        grade = "ASSERTED"
    else:
        grade = "UNKNOWN"

    return {
        "run_id": meta.get("run_id", UNKNOWN_VALUE),
        "start_ts": meta.get("start_ts", UNKNOWN_VALUE),
        "certification": {
            "runtime_observed": "PASS" if rt.get("success_rate") is not None else "UNKNOWN",
            "evidence_complete": "PASS" if (completed and artifacts >= completed) else "FAIL",
            "reproducibility": {
                "commit_frozen": commit_frozen,
                "dirty_tree": dirty,
                "head_changed": head["changed"],
                "reproducibility_grade": grade,
                "reasons": repro["reasons"],
                "commits_during_run": head["commits_during_run"],
            },
        },
        "execution_context": ctx,
        "memory": mem,
        "resource_trend": trend,
        "runtime_snapshot": {
            "uptime_hms": snap.get("uptime_hms"),
            "completed": completed,
            "passed": rt.get("passed_total"),
            "failed": rt.get("failed_total"),
            "success_rate": rt.get("success_rate"),
            "low_water": meta.get("low_water"),
            "high_water": meta.get("high_water"),
            "evidence_artifacts": artifacts,
        },
    }


def to_yaml(rep: Dict[str, Any]) -> str:
    c = rep["certification"]
    r = c["reproducibility"]
    lines = [
        "Certification:",
        f"  run_id: {rep['run_id']}",
        f"  runtime_observed: {c['runtime_observed']}",
        f"  evidence_complete: {c['evidence_complete']}",
        "  reproducibility:",
        f"    commit_frozen: {str(r['commit_frozen']).lower()}",
        f"    dirty_tree: {str(r['dirty_tree']).lower()}",
        f"    head_changed: {str(r['head_changed']).lower()}",
        f"    reproducibility_grade: {r['reproducibility_grade']}",
    ]
    if r["reasons"]:
        lines.append("    reasons:")
        lines.extend(f"      - {x}" for x in r["reasons"])
    m = rep["memory"]
    lines += [
        "  memory:",
        f"    pattern: {m['pattern']}",
        f"    floor_drift_pts: {m.get('floor_drift_pts')}",
        f"    spread_pts: {m.get('spread_pts')}",
        f"    latest: {m.get('latest')}",
        f"    note: {m.get('note')}",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", default="coordination/soak")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    rep = build(a.run_dir)
    if a.json:
        print(json.dumps(rep, indent=2))
        return 0
    print(to_yaml(rep))
    print("\n  resource trend (10-min windows)")
    print(f"  {'window':<12}{'mem%':>7}{'memMax':>8}{'rssMax':>8}{'wal':>7}{'queue':>7}{'done':>6}{'fail':>6}{'p95':>7}")
    for w in rep["resource_trend"]:
        print(f"  {w['window']:<12}{w['sys_mem_pct_mean'] or 0:>7.1f}{w['sys_mem_pct_max'] or 0:>8.1f}"
              f"{w['daemon_rss_mb_max'] or 0:>8.1f}{w['wal_mb'] or 0:>7.2f}{w['queue_depth'] or 0:>7}"
              f"{w['completed'] or 0:>6}{w['failed'] or 0:>6}{w['p95_latency_s'] or 0:>7.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
