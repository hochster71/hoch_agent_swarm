"""HERMES Capability Map — capability → WORKER selection.

IMPORTANT (anti-duplication): HELM ALREADY HAS a capability registry —
`backend/helm_runtime/capability_registry.py` (frozen), backed by
`coordination/governance/capability_registry.json`, which maps capability → ROLE.
That module and its data are NOT modified and NOT replaced.

HERMES composes over it to close the missing half:
        capability ──(frozen registry)──▶ role ──(HERMES)──▶ concrete WORKER
The frozen layer keeps owning capability→role. HERMES owns worker selection, which
never existed before (workers had no manifests to select from).

Selection is explainable: every choice returns the reason and the rejected candidates.
NO FAKE GREEN: if no observed-available worker advertises the capability, HERMES returns
resolved=False with the reason — it never silently substitutes an unrelated worker.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.hermes.worker_registry import list_workers

# Role → lane used by the existing guarded dispatch path (backend/dispatch/guarded_council).
ROLE_TO_LANE = {"orchestrator": "orchestrator", "builder": "builder",
                "auditor": "auditor", "local": "local"}

_COST_RANK = {"free": 0, "flat_max_plan": 1, "subscription": 2, "metered": 3}
_LAT_RANK = {"fast": 0, "medium": 1, "slow": 2}


def _frozen_role_for(capability: str) -> Dict[str, Any]:
    """Ask the EXISTING frozen capability registry which role owns this capability."""
    try:
        from backend.helm_runtime.capability_registry import route_capability
        return route_capability(capability)
    except Exception as e:
        return {"capability": capability, "resolved": False,
                "reason": f"frozen registry unavailable: {type(e).__name__}"}


def workers_for_capability(capability: str, *, include_unavailable: bool = False
                           ) -> List[Dict[str, Any]]:
    cap = (capability or "").strip().lower()
    out = []
    for w in list_workers():
        caps = [c.lower() for c in (w.get("capabilities") or [])]
        if cap not in caps:
            continue
        if not include_unavailable and w.get("availability") != "AVAILABLE":
            continue
        out.append(w)
    return out


def _score(w: Dict[str, Any], *, prefer_local: bool, need_context: int) -> tuple:
    """Lower is better. Local-first, then cheap, then fast, then bigger context."""
    local_pen = 0 if (w.get("locality") == "local") else 1
    if not prefer_local:
        local_pen = 0
    gate_pen = 1 if w.get("founder_gated") else 0
    ctx_ok = 0 if int(w.get("context_length") or 0) >= need_context else 1
    return (ctx_ok, local_pen, gate_pen,
            _COST_RANK.get(w.get("cost_class"), 9),
            _LAT_RANK.get(w.get("latency_class"), 9),
            -int(w.get("context_length") or 0))


def select_worker(capability: str, *, prefer_local: bool = True, need_context: int = 0,
                  exclude: Optional[List[str]] = None) -> Dict[str, Any]:
    """Resolve a capability to a concrete worker, with an explainable reason.

    Returns {resolved, worker, role, lane, reason, candidates, rejected}.
    """
    exclude = exclude or []
    frozen = _frozen_role_for(capability)
    role = frozen.get("role")

    candidates = [w for w in workers_for_capability(capability) if w["id"] not in exclude]
    if not candidates:
        blocked = workers_for_capability(capability, include_unavailable=True)
        return {
            "resolved": False, "capability": capability, "role": role,
            "reason": ("no worker advertises this capability"
                       if not blocked else
                       "workers advertise it but none are observed AVAILABLE"),
            "candidates": [], "blocked_candidates": [
                {"id": w["id"], "availability": w["availability"], "evidence": w.get("evidence")}
                for w in blocked],
            "frozen_route": frozen,
        }

    ranked = sorted(candidates, key=lambda w: _score(w, prefer_local=prefer_local,
                                                     need_context=need_context))
    best = ranked[0]
    lane = ROLE_TO_LANE.get(role or "", "local")
    why = []
    if best.get("locality") == "local" and prefer_local:
        why.append("local-first (no egress)")
    if best.get("cost_class") in ("free", "flat_max_plan"):
        why.append(f"cost={best.get('cost_class')}")
    if need_context:
        why.append(f"context {best.get('context_length')} >= required {need_context}")
    if best.get("founder_gated"):
        why.append("FOUNDER-GATED at the dispatch gateway")
    return {
        "resolved": True, "capability": capability, "role": role, "lane": lane,
        "worker": best, "worker_id": best["id"],
        "reason": "; ".join(why) or "highest-ranked available worker for this capability",
        "candidates": [w["id"] for w in ranked],
        "rejected": [w["id"] for w in ranked[1:]],
        "frozen_route": frozen,
    }


def capability_matrix() -> Dict[str, Any]:
    """Every capability HERMES can serve → which workers can serve it (observed)."""
    caps: Dict[str, Dict[str, Any]] = {}
    for w in list_workers():
        for c in (w.get("capabilities") or []):
            e = caps.setdefault(c, {"available": [], "unavailable": [], "role": None})
            (e["available"] if w["availability"] == "AVAILABLE" else e["unavailable"]).append(w["id"])
    for c, e in caps.items():
        e["role"] = _frozen_role_for(c).get("role")
        e["servable"] = bool(e["available"])
    return {"schema": "HERMES_CAPABILITY_MATRIX_v1", "capabilities": caps,
            "note": "role column comes from the FROZEN capability_registry (unmodified)"}
