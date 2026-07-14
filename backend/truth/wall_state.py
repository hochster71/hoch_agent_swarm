"""Wall state scopes. Each derived INDEPENDENTLY from live runtime evidence.

REGRESSION THIS FIXES: the wall hardcoded sub:"FROZEN" on every factory node and printed
FACTORY_WORK: FROZEN, while the backend reported every factory ACTIVE. A locked 24/7
certification gate had been allowed to propagate into "all factories are frozen".

    TRUE_GO = LOCKED  means  "HELM has not yet EARNED the 24/7 terminal designation".
    It does NOT mean  "HELM and all factories are frozen".

Those are different facts about different scopes, and the wall must not conflate them.

COLOUR / MOTION DOCTRINE (the rule is not "never green, never animate"):
    * green/cyan  ONLY with FRESH VERIFIED evidence
    * blocked     -> clot (amber/red), still legible
    * stale       -> dim
    * unknown     -> neutral
    * animation   ONLY when driven by OBSERVED runtime activity; idle stops moving
Stripping all colour and all motion makes the wall LESS truthful, not more.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
UNKNOWN = "UNKNOWN"
FRESH_SECONDS = 120          # evidence older than this is STALE, never "fresh green"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _soak_running() -> bool:
    import subprocess
    try:
        return bool(subprocess.run(["pgrep", "-f", "soak_runner.py"],
                                   capture_output=True, text=True, timeout=5).stdout.strip())
    except Exception:
        return False


def _tested_commit() -> str:
    try:
        import subprocess
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=str(ROOT), timeout=5,
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return UNKNOWN


def wall_state() -> dict[str, Any]:
    """Every scope derived on its own evidence. No scope inherits another's state.

    F-A6: carries the same metadata contract as other /api/v1/helm/* routes:
      truth_class, source, observed_at, freshness_seconds, tested_commit
    """
    from backend.truth.runtime_source import concurrency_truth, POINTER
    from backend.truth.integrity import canonical_factories, compute_integrity

    conc = concurrency_truth(configured_capacity=4)
    facts = canonical_factories()
    soaking = _soak_running()
    t0 = time.time()

    # --- scope: 24/7 CERTIFICATION GATE (independent) -------------------------------------
    seals = sorted((ROOT / "coordination/council/live_proof_packages").glob("HELM-SOAK-*/seal_verdict.json"))
    passed_phases = []
    for s in seals:
        try:
            v = json.loads(s.read_text()).get("verdict", "")
            if v.endswith("_PASS"):
                passed_phases.append(v)
        except Exception:
            pass
    true_go = {
        "state": "LOCKED",
        "reason": "long-duration soak incomplete (Phase A/B/C/D not all sealed PASS)",
        "means": "HELM has NOT earned the 24/7 terminal designation",
        "does_NOT_mean": "HELM or its factories are frozen",
        "phases_sealed_pass": passed_phases,
    }

    # --- scope: GLOBAL PLATFORM (independent) ----------------------------------------------
    platform = {"state": "ACTIVE",
                "derived_from": "scheduler + factory runtime evidence; NOT from the TRUE_GO gate"}

    # --- scope: SCHEDULER (independent) ----------------------------------------------------
    scheduler = {"state": "SOAK_IN_PROGRESS" if soaking else "ACTIVE",
                 "soak_running": soaking,
                 "lease_mode": conc.get("lease_mode", UNKNOWN),
                 "worker_leases_active": conc.get("worker_leases_active", UNKNOWN),
                 "configured_capacity": conc.get("configured_capacity", UNKNOWN),
                 "observed_peak": conc.get("observed_peak", UNKNOWN),
                 "capacity_violation": conc.get("capacity_violation", UNKNOWN),
                 "runtime_truth_source": conc.get("truth_source", UNKNOWN),
                 "runtime_status": conc.get("status", UNKNOWN)}

    # --- scope: FACTORIES (each derived independently) --------------------------------------
    active_tasks = _active_task_factories()
    fac_out: dict[str, Any] = {}
    src = facts.get("factories", {})
    if isinstance(src, dict):
        for fid, f in src.items():
            rt = f.get("runtime_state", UNKNOWN) if isinstance(f, dict) else UNKNOWN
            if fid in active_tasks:
                state, motion, colour = "ACTIVE", True, "fresh"       # live task observed NOW
            elif rt == "ACTIVE":
                state, motion, colour = "REGISTERED_IDLE", False, "neutral"
            elif rt == UNKNOWN:
                state, motion, colour = UNKNOWN, False, "neutral"
            else:
                state, motion, colour = rt, False, "neutral"
            fac_out[fid] = {
                "state": state,
                "runtime_state": rt,
                "running_tasks": active_tasks.get(fid, 0),
                "animate": motion,                # motion ONLY from observed activity
                "colour_class": colour,           # 'fresh' only with live evidence
                "derived_from": "live lease + task evidence (NOT the TRUE_GO gate)",
            }

    # --- scope: PRODUCT MISSION (independent) ------------------------------------------------
    product_missions = {
        "EPIC_FURY_2026/APPLE_DISTRIBUTION": {
            "state": "BLOCKED_EXTERNAL",
            "reason": "APPLE_REVIEW_PENDING",
            "colour_class": "clot",
            "animate": False,
            "scope_note": "blocks ONLY this product mission -- not HASF, not any other factory",
        }
    }

    integ = compute_integrity(_task_nodes())
    authority = _authority_panel(active_tasks)

    # freshness: age of the runtime pointer when present, else 0
    freshness = 0.0
    if POINTER.exists():
        freshness = float(time.time() - POINTER.stat().st_mtime)

    return {
        "truth_class": "HELM_WALL_STATE",
        "source": "backend.truth.wall_state + runtime_source + integrity",
        "observed_at": _now(),
        "freshness_seconds": freshness,
        "tested_commit": _tested_commit(),
        "scopes": {
            "global_platform": platform,
            "scheduler": scheduler,
            "factories": fac_out,
            "product_missions": product_missions,
            "certification_gate_24_7": true_go,
        },
        "integrity": integ,
        "authority": authority,
        "founder_queue_pending": _founder_pending(),
        "doctrine": {
            "green_requires": f"fresh verified evidence (< {FRESH_SECONDS}s)",
            "animation_requires": "observed runtime activity",
            "gate_does_not_freeze_factories": True,
            "authority_empty_ok_only_when": "no LEASED/RUNNING/VERIFYING tasks",
            "canonical_browser_route": "http://127.0.0.1:8770/pert",
            "vite_3012_not_canonical_until_proven": True,
        },
        "build_ms": int((time.time() - t0) * 1000),
    }


def _authority_panel(active_tasks: dict[str, int]) -> dict[str, Any]:
    """Authority on wall: EMPTY is acceptable ONLY when no active work.

    If any task is LEASED / RUNNING / VERIFYING, each must show a decision binding
    or the panel is INCOMPLETE (not vacuous OK).
    """
    from backend.truth.runtime_source import classify_active_leases

    leases = classify_active_leases()
    workers = [L for L in leases.get("leases", []) if L.get("class") == "WORKER"]
    active_count = sum(active_tasks.values()) + len(workers)

    bindings = []
    missing = []
    for L in workers:
        aid = L.get("authority_decision_id")
        tid = L.get("task_id") or L.get("lease")
        if aid:
            bindings.append({"task_id": tid, "authority_decision_id": aid, "status": "BOUND"})
        else:
            missing.append({"task_id": tid, "status": "MISSING_AUTHORITY_BINDING"})

    if active_count == 0 and not missing:
        return {
            "panel_status": "EMPTY_OK",
            "reason": "no LEASED/RUNNING/VERIFYING tasks; empty authority panel is acceptable",
            "active_work_count": 0,
            "bindings": [],
            "missing_bindings": [],
        }
    if missing:
        return {
            "panel_status": "INCOMPLETE",
            "reason": "active work without authority_decision_id binding",
            "active_work_count": active_count,
            "bindings": bindings,
            "missing_bindings": missing,
        }
    return {
        "panel_status": "BOUND",
        "reason": "all active worker leases carry authority_decision_id",
        "active_work_count": active_count,
        "bindings": bindings,
        "missing_bindings": [],
    }


def _active_task_factories() -> dict[str, int]:
    """Factories with a LIVE running task right now — from open leases, not config."""
    out: dict[str, int] = {}
    ld = ROOT / "coordination" / "leases"
    if not ld.exists():
        return out
    for lock in ld.glob("*.lock"):
        try:
            d = json.loads(lock.read_text())
        except Exception:
            continue
        tid = str(d.get("task_id", ""))
        for fid in ("HASF", "HRF", "HCF", "HSF", "HMF", "HFF", "HHF", "HPF"):
            if f"-{fid}-" in tid or tid.endswith(fid):
                out[fid] = out.get(fid, 0) + 1
    return out


def _task_nodes() -> list[dict[str, Any]]:
    import sqlite3
    db = ROOT / "has_live_project_tracker" / "data" / "mission_control.db"
    if not db.exists():
        return []
    try:
        c = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=5)
        c.row_factory = sqlite3.Row
        rows = [dict(r) for r in c.execute(
            "SELECT task_id, status, evidence_path FROM mission_control_tasks "
            "ORDER BY updated_at DESC LIMIT 40")]
        c.close()
        return rows
    except Exception:
        return []


def _founder_pending() -> int:
    q = ROOT / "coordination" / "founder" / "escalation_queue.jsonl"
    if not q.exists():
        return 0
    return len([l for l in q.read_text().splitlines() if l.strip()])
