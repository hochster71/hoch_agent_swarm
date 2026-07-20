"""HERMES Dispatcher — dispatch(capability=...), never dispatch_to_<vendor>().

THE ONE RULE: HERMES selects; it does NOT execute. Execution stays on the EXISTING
guarded path so there is exactly one choke point in HELM:

    dispatch(capability) ──▶ capability_map.select_worker()   [HERMES: selection]
                         ──▶ guarded_council.guarded_dispatch(lane, prompt)
                         ──▶ scripts/council/gateway.CouncilDispatchGateway
                             [EXISTING: allowlist, cost cap, egress guard, ledger]

NO new queue, scheduler, event bus, or adapter interface is created here — the gateway
and dispatch_gateway.ProviderAdapter already own those.

NO FAKE GREEN: if no worker is available for the capability, this returns
resolved=False / ok=False with the reason and the blocked candidates. It never
silently falls back to an unrelated worker, and every fallback that DOES happen is
recorded explicitly (fallback_used, fallback_reason).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.hermes.capability_map import select_worker
from backend.hermes.learning import record_mission


def dispatch(capability: str, prompt: str, *, prefer_local: bool = True,
             need_context: int = 0, allow_fallback: bool = True,
             timeout: int = 300, pert_node: str = "HERMES") -> Dict[str, Any]:
    """Dispatch BY CAPABILITY. The runtime chooses the worker."""
    import time
    t0 = time.time()
    tried: List[str] = []
    fallback_used = False
    fallback_reason = None

    sel = select_worker(capability, prefer_local=prefer_local, need_context=need_context)
    if not sel.get("resolved"):
        out = {"ok": False, "capability": capability, "resolved": False,
               "error": "no_worker_for_capability", "reason": sel.get("reason"),
               "blocked_candidates": sel.get("blocked_candidates", [])}
        record_mission(capability=capability, worker=None, ok=False,
                       latency_ms=int((time.time() - t0) * 1000),
                       selection_reason=sel.get("reason"), fallback_used=False,
                       verification=None, error="no_worker_for_capability")
        return out

    while True:
        worker = sel["worker"]; wid = sel["worker_id"]; lane = sel["lane"]
        tried.append(wid)
        from backend.dispatch.guarded_council import guarded_dispatch  # existing choke point
        res = guarded_dispatch(lane, prompt, pert_node=pert_node, timeout=timeout)
        latency_ms = int((time.time() - t0) * 1000)

        if res.get("ok") or not allow_fallback:
            out = {
                "ok": bool(res.get("ok")), "capability": capability, "resolved": True,
                "worker_id": wid, "worker": worker.get("display_name"),
                "lane": lane, "role": sel.get("role"),
                "selection_reason": sel.get("reason"),
                "fallback_used": fallback_used, "fallback_reason": fallback_reason,
                "tried": tried, "latency_ms": latency_ms,
                "text": res.get("text"), "model": res.get("model"),
                "provider": res.get("provider"),
                "gateway": {k: res.get(k) for k in ("blocked", "error", "dispatch_type") if res.get(k)},
            }
            record_mission(capability=capability, worker=wid, ok=bool(res.get("ok")),
                           latency_ms=latency_ms, selection_reason=sel.get("reason"),
                           fallback_used=fallback_used, verification=None,
                           error=res.get("error") or res.get("blocked"))
            return out

        # failed → try the next candidate, explicitly recorded as a fallback
        fallback_used = True
        fallback_reason = res.get("error") or res.get("blocked") or "worker_failed"
        sel = select_worker(capability, prefer_local=prefer_local,
                            need_context=need_context, exclude=tried)
        if not sel.get("resolved"):
            out = {"ok": False, "capability": capability, "resolved": True,
                   "error": "all_workers_failed", "tried": tried,
                   "fallback_used": True, "fallback_reason": fallback_reason,
                   "latency_ms": int((time.time() - t0) * 1000)}
            record_mission(capability=capability, worker=tried[-1] if tried else None,
                           ok=False, latency_ms=out["latency_ms"],
                           selection_reason="exhausted", fallback_used=True,
                           verification=None, error="all_workers_failed")
            return out


def explain(capability: str, *, prefer_local: bool = True, need_context: int = 0) -> Dict[str, Any]:
    """Dry-run: who WOULD be selected and why. Dispatches nothing."""
    sel = select_worker(capability, prefer_local=prefer_local, need_context=need_context)
    return {"schema": "HERMES_SELECTION_EXPLAIN_v1", **sel, "dispatched": False}
