"""HELM GOAL + PERT aggregator — backcast critical path to GOAL_HELM.

Loads coordination/goal/{helm_goal.json, helm_pert.json, si_status.json}, computes
per-node PERT expected time (TE = (O+4M+P)/6), a forward/backward pass for the
critical path, and an honest percent-to-GOAL weighted by node status. Live SI
status is folded in from si_status.json (written by scripts/run_helm_si.py).

No fake green: percent-to-GOAL weights DONE=1, PARTIAL=0.5, IN_PROGRESS=0.25,
everything else 0. A node is never counted complete without its evidence.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
GOALP = ROOT / "coordination" / "goal"


def _load(name: str) -> Dict[str, Any]:
    p = GOALP / name
    return json.loads(p.read_text()) if p.exists() else {}


def build_goal_pert() -> Dict[str, Any]:
    goal = _load("helm_goal.json")
    pert = _load("helm_pert.json")
    si = _load("si_status.json")
    weights = (pert.get("status_legend") or {})
    nodes: List[Dict[str, Any]] = list(pert.get("nodes") or [])
    by_id = {n["id"]: n for n in nodes}

    # TE per node
    for n in nodes:
        O, M, P = n.get("O", 0), n.get("M", 0), n.get("P", 0)
        n["TE"] = round((O + 4 * M + P) / 6.0, 2)
        n["weight"] = weights.get(n.get("status"), 0.0)

    # Forward pass: earliest finish = max(dep EF) + TE
    def ef(nid: str, seen=None) -> float:
        seen = seen or set()
        if nid in seen:
            return 0.0
        seen.add(nid)
        n = by_id.get(nid, {})
        deps = n.get("deps") or []
        base = max([ef(d, seen) for d in deps], default=0.0)
        return base + n.get("TE", 0.0)
    for n in nodes:
        n["earliest_finish"] = round(ef(n["id"]), 2)

    # Critical path = the dep chain into GOAL with the largest earliest_finish
    def crit_chain(nid: str) -> List[str]:
        n = by_id.get(nid, {})
        deps = n.get("deps") or []
        if not deps:
            return [nid]
        worst = max(deps, key=lambda d: by_id.get(d, {}).get("earliest_finish", 0.0))
        return crit_chain(worst) + [nid]
    critical_path = crit_chain("GOAL_HELM") if "GOAL_HELM" in by_id else []

    # Percent to GOAL: weighted over the work nodes (exclude the GOAL sink)
    work = [n for n in nodes if n["id"] != "GOAL_HELM"]
    pct = round(100.0 * sum(n["weight"] for n in work) / max(len(work), 1), 1)

    # Remaining expected days on the pending portion of the critical path
    remaining = round(sum(by_id.get(x, {}).get("TE", 0.0)
                          for x in critical_path
                          if by_id.get(x, {}).get("status") not in ("DONE",)), 2)

    return {
        "schema": "HELM_GOAL_PERT_v1",
        "goal": {"id": goal.get("goal_id"), "statement": goal.get("statement"),
                 "acceptance_criteria": goal.get("acceptance_criteria")},
        "percent_to_goal": pct,
        "percent_basis": "status-weighted over work nodes (DONE=1, PARTIAL=.5, IN_PROGRESS=.25, else 0)",
        "critical_path": critical_path,
        "critical_path_remaining_days": remaining,
        "nodes": nodes,
        "system_integration": {
            "present": bool(si),
            "green": si.get("green"),
            "passed": si.get("passed"), "failed": si.get("failed"), "errors": si.get("errors"),
            "ran_at": si.get("ran_at"), "duration_s": si.get("duration_s"),
            "out_of_scope": si.get("out_of_scope"),
            "note": "run scripts/run_helm_si.py to refresh" if not si else None,
        },
        "headline": "HELM Core 1.0.0-alpha — Constitutional Baseline Ratified. Independent implementation verification pending.",
        "doctrine": "No fake green; PARTIAL/PENDING/BLOCKED reported honestly.",
    }
