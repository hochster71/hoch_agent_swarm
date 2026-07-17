"""Mission State routes — shared truth surface for main API (:8000) and tests.

Same engine as helm_live_api: backend.mission_control.mission_state.write_mission_state.
No alternate computation path. No fake green.
"""
from __future__ import annotations

import datetime
from typing import Any, Dict

from fastapi import APIRouter
from fastapi.responses import JSONResponse, PlainTextResponse

router = APIRouter(tags=["mission-state"])
UNKNOWN = "UNKNOWN"


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _truth_response(
    truth_class: str,
    source: str,
    observed_at: str,
    freshness_seconds: float | None,
    data: dict,
) -> dict:
    return {
        "truth_class": truth_class,
        "source": source,
        "observed_at": observed_at,
        "freshness_seconds": freshness_seconds,
        **data,
    }


@router.get("/api/v1/helm/mission")
@router.get("/api/v1/helm/mission/state")
@router.get("/api/mission/state")
def api_mission_state() -> JSONResponse:
    """Single operational mission view — identical engine as HELM LIVE :8770."""
    from backend.mission_control.mission_state import write_mission_state

    try:
        state = write_mission_state()
        return JSONResponse(
            _truth_response(
                truth_class="HELM_MISSION_STATE",
                source="coordination/goal/mission_state.json",
                observed_at=_now(),
                freshness_seconds=0.0,
                data=state,
            )
        )
    except Exception as e:
        return JSONResponse(
            _truth_response(
                truth_class="HELM_MISSION_STATE",
                source="backend.mission_control.mission_state",
                observed_at=_now(),
                freshness_seconds=None,
                data={"state": UNKNOWN, "reason": str(e)},
            )
        )


@router.get("/api/v1/helm/mission/executive")
@router.get("/api/mission/executive")
def api_mission_executive() -> PlainTextResponse:
    from backend.mission_control.mission_state import render_executive_text, write_mission_state

    try:
        st = write_mission_state()
        return PlainTextResponse(render_executive_text(st), media_type="text/plain; charset=utf-8")
    except Exception as e:
        return PlainTextResponse(f"MISSION STATE UNKNOWN\n{e}\n", status_code=500)
