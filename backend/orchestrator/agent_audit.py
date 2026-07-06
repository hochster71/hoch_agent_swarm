"""HOCH agent-activity audit — what's ACTIVE, what's DORMANT, and the work left to GOAL.

Honest answer to 'why aren't they all continuously improving?': the system is INTERVAL-driven
(launchd every 10 min), single-process, mechanical — not literally 'unlimited agents' running in
parallel. This audit reports, from REAL state (file mtimes + convergence + orchestrator + gaps),
which components are actually producing work, which are idle or not-yet-built, and what remains to
reach each GOAL. Deterministic, no fabrication — an UNKNOWN reads UNKNOWN.
"""
import json
import time
import datetime
from pathlib import Path
from typing import Dict, Any, List

from backend.factory.registry import list_factories

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data" / "prompt_brain"
FRESH_S = 15 * 60   # a component that produced output within 15 min counts as ACTIVE


def _age_s(p: Path):
    try:
        return time.time() - Path(p).stat().st_mtime
    except Exception:
        return None


def _load(p, d):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return d


def audit() -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []

    # Factories
    for f in list_factories():
        conv = _load(f.convergence_status, {})
        age = _age_s(f.convergence_status)
        state = conv.get("state", "SEEDED")
        active = age is not None and age < FRESH_S and state in ("IMPROVING",)
        rows.append({
            "agent": f"{f.code} factory ({f.domain})",
            "status": "ACTIVE" if active else ("IDLE" if age is not None else "DORMANT"),
            "state": state, "last_activity_s": round(age) if age else None,
            "goal_aligned": True,
            "work_left": ("improving" if state == "IMPROVING"
                          else "at proxy ceiling — needs frontier judge (cost)" if state in ("STALLED_NO_IMPROVER", "CONVERGED", "SELECTED")
                          else "run cycles"),
        })

    # AI Michael orchestrator
    ob = _load(DATA / "orchestrator_brief.json", {})
    age = _age_s(DATA / "orchestrator_brief.json")
    rows.append({
        "agent": "AI Michael (founder orchestrator)",
        "status": "ACTIVE" if (age and age < FRESH_S) else "IDLE",
        "state": (ob.get("next_move") or {}).get("action", "—"),
        "last_activity_s": round(age) if age else None, "goal_aligned": True,
        "work_left": "RECOMMENDS but does not yet EXECUTE — auto-execute is the autonomy gap",
    })

    # Cadence mechanism (interval vs continuous)
    cadence_log = ROOT / "data" / "backups" / "brain_cadence.log"
    age = _age_s(cadence_log)
    rows.append({
        "agent": "cadence loop",
        "status": "ACTIVE" if (age and age < FRESH_S) else "IDLE",
        "state": "10-min launchd interval (NOT continuous)",
        "last_activity_s": round(age) if age else None, "goal_aligned": True,
        "work_left": "convert to a continuous KeepAlive daemon so cycles run back-to-back",
    })

    # Cyber swarm (Red/Blue/Purple)
    swarm_state = DATA / "cyber_swarm_state.json"
    exists = swarm_state.exists()
    rows.append({
        "agent": "Cyber Swarm (Red/Blue/Purple)",
        "status": "ACTIVE" if exists and (_age_s(swarm_state) or 1e9) < FRESH_S else ("IDLE" if exists else "NOT_BUILT"),
        "state": _load(swarm_state, {}).get("verdict", "—") if exists else "—",
        "last_activity_s": round(_age_s(swarm_state)) if exists else None, "goal_aligned": True,
        "work_left": "continuous adversarial hardening of HAS + products (real scanners + seeded faults)",
    })

    active = sum(1 for r in rows if r["status"] == "ACTIVE")
    idle = sum(1 for r in rows if r["status"] == "IDLE")
    dormant = sum(1 for r in rows if r["status"] in ("DORMANT", "NOT_BUILT"))

    out = {
        "schema": "hoch-agent-audit-v1",
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "totals": {"active": active, "idle": idle, "dormant": dormant, "components": len(rows)},
        "missing_for_full_autonomy": [
            "continuous daemon (not 10-min interval)",
            "AI Michael auto-executes autonomous $0 actions (stop asking)",
            "Cyber Swarm running continuously (Red/Blue/Purple)",
            "frontier judges for HMF/HRF real gains (cost decision)",
        ],
        "agents": rows,
    }
    (DATA).mkdir(parents=True, exist_ok=True)
    (DATA / "agent_audit.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


if __name__ == "__main__":
    a = audit()
    t = a["totals"]
    print(f"HOCH AGENT AUDIT — {t['active']} active · {t['idle']} idle · {t['dormant']} dormant "
          f"of {t['components']} components")
    for r in a["agents"]:
        la = f"{r['last_activity_s']}s ago" if r["last_activity_s"] is not None else "never"
        print(f"  [{r['status']:8}] {r['agent']:38} · {r['state'][:32]:32} · last {la}")
        print(f"             work left: {r['work_left']}")
    print("\n  MISSING FOR FULL AUTONOMY:")
    for m in a["missing_for_full_autonomy"]:
        print(f"   - {m}")
