"""Ready-to-mount FastAPI router for the runtime-freshness service.

NOT wired into the running app on purpose — the live Phase C soak must not be
restarted. To activate on the next SAFE restart, add ONE line to the app that
owns /api/v1/helm/* (backend/helm_live_api.py or backend/main.py):

    from backend.runtime_freshness_api import router as freshness_router
    app.include_router(freshness_router)

That exposes:  GET /api/v1/helm/freshness  ->  evaluate_all()

UIs badge off it: overall_state drives a page-level FRESH/STALE/UNKNOWN banner, and
each panel greys + shows "stale Ns" when its matching signal is STALE, or hatches
"UNKNOWN" when the signal is UNKNOWN (never render UNKNOWN as live).
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.runtime_freshness import evaluate_all

router = APIRouter()


@router.get("/api/v1/helm/freshness")
def api_v1_freshness() -> JSONResponse:
    """Per-signal freshness with tight budgets; overall = worst signal. Read-only."""
    return JSONResponse(evaluate_all())
