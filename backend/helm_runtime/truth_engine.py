"""Runtime Truth Engine — compute projections; never invent green.

This engine does not "act" as Truth. It derives projections from evidence sources.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[2]


def recompute_projections(mission_id: Optional[str] = None) -> Dict[str, Any]:
    """Recompute derived truth. Failures become explicit UNKNOWN/error fields."""
    out: Dict[str, Any] = {
        "engine": "runtime_truth_engine",
        "is_actor": False,
        "doctrine": "truth_is_derived_not_owned",
        "projections": {},
        "errors": [],
    }
    # Mission state (derived dashboard projection)
    try:
        from backend.mission_control.mission_state import build_mission_state

        ms = build_mission_state(mission_id=mission_id)
        out["projections"]["mission_state"] = {
            "schema": ms.get("schema"),
            "overall": (ms.get("overall") or {}).get("status"),
            "mission_id": (ms.get("mission") or {}).get("id"),
            "source": "coordination/goal/mission_state.json",
            "class": "PROJECTION",
        }
        # Persist derived projection (existing atomic writer)
        from backend.mission_control.mission_state import write_mission_state

        write_mission_state(mission_id=mission_id)
    except Exception as e:
        out["errors"].append(f"mission_state: {type(e).__name__}: {e}")
        out["projections"]["mission_state"] = {"class": "UNKNOWN", "error": str(e)[:200]}

    # External milestones
    try:
        from backend.truth.external_milestones import compute_external_milestones

        ext = compute_external_milestones()
        out["projections"]["external_milestones"] = {
            "class": "PROJECTION",
            "release": ((ext.get("milestones") or {}).get("RELEASE") or {}).get("current_state"),
            "revenue": ((ext.get("milestones") or {}).get("REVENUE") or {}).get("current_state"),
        }
    except Exception as e:
        out["errors"].append(f"external: {type(e).__name__}: {e}")
        out["projections"]["external_milestones"] = {"class": "UNKNOWN", "error": str(e)[:200]}

    # HMAI
    try:
        from backend.truth.hmai import compute_hmai

        h = compute_hmai()
        out["projections"]["hmai"] = {
            "class": "PROJECTION",
            "index": h.get("index"),
            "band": h.get("band"),
            "can_proceed": h.get("can_mission_safely_proceed"),
        }
    except Exception as e:
        out["errors"].append(f"hmai: {type(e).__name__}: {e}")
        out["projections"]["hmai"] = {"class": "UNKNOWN", "error": str(e)[:200]}

    return out
