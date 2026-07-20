"""Knowledge API — the read-only HTTP surface of the Knowledge Engine (EDR-0004).

Exposes governed retrieval so every worker resolves the SAME authoritative
knowledge over one door instead of depending on private chat history:

  GET /api/v1/helm/knowledge?q=…&kind=…   → ranked governed docs (provenance+freshness)
  GET /api/v1/helm/knowledge/manifest      → the indexed corpus manifest
  GET /api/v1/helm/knowledge/session-load  → Constitution + applicable EDRs in one call

Every route here is READ-ONLY. Ingestion (the only state-changing path) is not
exposed as HTTP — it runs governance-checked in-process via
``knowledge_engine.ingest`` and emits an Event Bus event. This is a separate,
non-frozen module (like ``normalization.py``); it never touches the frozen
verification target.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

try:
    from fastapi import APIRouter, HTTPException, Query

    _HAVE_FASTAPI = True
except Exception:  # pragma: no cover - import guard for envs without fastapi
    _HAVE_FASTAPI = False

from backend.helm_runtime import knowledge_engine as ke


if _HAVE_FASTAPI:

    def build_router() -> "APIRouter":
        router = APIRouter(prefix="/api/v1/helm/knowledge", tags=["helm-knowledge-engine"])

        @router.get("")
        def get_knowledge(
            q: str = Query(..., description="governance-provenance question / keywords"),
            kind: Optional[str] = Query(default=None, description="filter: edr|constitution|evidence|…"),
            limit: int = Query(default=8, ge=1, le=50),
            role: Optional[str] = Query(default=None, description="requesting actor role (optional)"),
        ) -> Dict[str, Any]:
            result = ke.retrieve(q, kind=kind, limit=limit, role=role)
            if result.get("status") == "ROLE_REJECTED":
                raise HTTPException(status_code=403, detail=result)
            return result

        @router.get("/manifest")
        def get_manifest(kind: Optional[str] = Query(default=None)) -> Dict[str, Any]:
            man = ke.build_manifest()
            if kind:
                docs = [d for d in man["documents"] if d["kind"] == kind]
                man = {**man, "documents": docs, "document_count": len(docs), "kind_filter": kind}
            return man

        @router.get("/session-load")
        def get_session_load() -> Dict[str, Any]:
            return ke.governed_load_constitution_and_edrs()

        return router


def router_or_none():
    """Return the APIRouter if FastAPI is available, else None (host mounts if present)."""
    if _HAVE_FASTAPI:
        return build_router()
    return None
