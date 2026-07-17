"""Bridge API — the role-based HTTP surface of the HELM runtime.

Exposes the runtime bridge as a FastAPI router so ChatGPT (Orchestrator),
Claude (Builder), and Grok (Auditor) each talk to HELM over the same governed
door instead of to each other:

  GET   /api/v1/helm/mission          → versioned mission + projection hint (read)
  PATCH /api/v1/helm/mission          → role-tagged, version-pinned proposal (write)
  GET   /api/v1/helm/events           → tail of the event bus (nervous system)
  GET   /api/v1/helm/providers        → provider health (adapter-level; no secrets)
  GET   /api/v1/helm/workers          → per-role worker health (≠ provider health)
  GET   /api/v1/helm/mission-health   → dark-UI executive mission health projection
  GET   /api/v1/helm/capabilities     → capability registry (brand-agnostic)
  GET   /api/v1/helm/bridge           → routing status (how to submit a proposal)
  GET   /api/v1/helm/timeline         → mission timeline from event bus

The PATCH path is optimistic-concurrency: the client sends the mission_version
it read; a stale version returns HTTP 409. Founder-gate fields require an
explicit founder authorization header — every other write is delegated.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from fastapi import APIRouter, Body, Header, HTTPException
    from pydantic import BaseModel

    _HAVE_FASTAPI = True
except Exception:  # pragma: no cover - import guard for envs without fastapi
    _HAVE_FASTAPI = False

from backend.helm_runtime.event_bus import tail_events
from backend.helm_runtime.mission_store import read_mission
from backend.helm_runtime.mission_runtime import mission_projection_hint
from backend.helm_runtime.provider_router import worker_health
from backend.helm_runtime.role_router import route_proposal, routing_status
from backend.helm_runtime.dispatch_gateway import default_gateway
from backend.helm_runtime.capability_registry import all_capabilities


def _mission_view() -> Dict[str, Any]:
    doc = read_mission()
    hint = mission_projection_hint()
    return {
        "mission_version": doc.get("mission_version"),
        "transaction_id": doc.get("transaction_id"),
        "state": doc.get("state"),
        "operational_status": doc.get("operational_status"),
        "mission": doc.get("mission"),
        "critical_path": doc.get("critical_path"),
        "external_gates": doc.get("external_gates"),
        "projection_hint": hint,
        "occ_note": "PATCH must send expected_parent_version = this mission_version",
    }


if _HAVE_FASTAPI:

    class ProposalIn(BaseModel):
        role: str
        patch: Dict[str, Any]
        expected_parent_version: Optional[int] = None
        actor: Optional[str] = None
        evidence: Optional[List[str]] = None
        note: str = ""
        correlation_id: Optional[str] = None

    def build_router() -> "APIRouter":
        router = APIRouter(prefix="/api/v1/helm", tags=["helm-runtime-bridge"])

        @router.get("/mission")
        def get_mission() -> Dict[str, Any]:
            return _mission_view()

        @router.patch("/mission")
        def patch_mission(
            proposal: ProposalIn = Body(...),
            x_helm_founder_authorization: Optional[str] = Header(default=None),
        ) -> Dict[str, Any]:
            result = route_proposal(
                proposal.role,
                proposal.patch,
                expected_parent_version=proposal.expected_parent_version,
                actor=proposal.actor,
                evidence=proposal.evidence,
                note=proposal.note,
                correlation_id=proposal.correlation_id,
                founder_token_present=bool(x_helm_founder_authorization),
            )
            status = result.get("status")
            if status == "CONFLICT":
                raise HTTPException(status_code=409, detail=result)
            if status == "ROLE_REJECTED":
                raise HTTPException(status_code=403, detail=result)
            if status == "MISSION_ABSENT":
                raise HTTPException(status_code=404, detail=result)
            if not result.get("ok"):
                raise HTTPException(status_code=422, detail=result)
            return result

        @router.get("/events")
        def get_events(n: int = 25) -> Dict[str, Any]:
            return {"events": tail_events(n=n), "source": "event_bus", "count_requested": n}

        @router.get("/providers")
        def get_providers() -> Dict[str, Any]:
            """Provider-level health (adapters). Distinct from per-role workers."""
            gw = default_gateway()
            return {
                "kind": "provider_health",
                "providers": gw.health(),
                "summary": gw.worker_status(),
                "binding_view": worker_health(),
                "doctrine": "no secrets returned; configured=env presence only",
            }

        @router.get("/workers")
        def get_workers() -> Dict[str, Any]:
            """Per-role worker health — configured / reachable / dispatch_enabled."""
            rows = default_gateway().worker_role_health()
            return {
                "kind": "worker_health",
                "workers": rows,
                "blocked": [w for w in rows if w.get("status") == "BLOCKED"],
                "available": [w for w in rows if w.get("status") == "AVAILABLE"],
            }

        @router.get("/mission-health")
        def get_mission_health() -> Dict[str, Any]:
            """Dark UI executive projection — operational status, not conversations."""
            return default_gateway().mission_health()

        @router.get("/capabilities")
        def get_capabilities() -> Dict[str, Any]:
            return {
                "kind": "capability_registry",
                "by_role": all_capabilities(),
                "note": "route by capability → role → binding; never by brand in callers",
            }

        @router.get("/timeline")
        def get_timeline(n: int = 40) -> Dict[str, Any]:
            """Mission timeline sourced entirely from the event bus (replayable)."""
            events = tail_events(n=n)
            # Chronological for UI (file is append-only chronological already)
            return {
                "kind": "mission_timeline",
                "source": "event_bus",
                "events": events,
                "count": len(events),
            }

        @router.get("/bridge")
        def get_bridge() -> Dict[str, Any]:
            return routing_status()

        return router


def router_or_none():
    """Return the APIRouter if FastAPI is available, else None (host mounts if present)."""
    if _HAVE_FASTAPI:
        return build_router()
    return None
