"""Mission Runtime — coordination surface for the versioned Executive Mission.

Platform engine (not an actor). Owns queues/proposals/commits via transactions.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[2]
EXEC_PATH = ROOT / "coordination" / "goal" / "executive_mission.json"


def load_mission(path: Path = EXEC_PATH) -> Dict[str, Any]:
    if not path.exists():
        return {"schema": "HELM_EXECUTIVE_MISSION_v1", "error": "missing", "path": str(path)}
    return json.loads(path.read_text(encoding="utf-8"))


def mission_projection_hint(path: Path = EXEC_PATH) -> Dict[str, Any]:
    """Hint for dashboards: Executive Mission is source of control; mission_state is projection."""
    doc = load_mission(path)
    return {
        "control_object": "executive_mission",
        "control_path": "coordination/goal/executive_mission.json",
        "projection_object": "mission_state",
        "projection_path": "coordination/goal/mission_state.json",
        "doctrine": "dashboard_is_projection_never_source",
        "mission_id": (doc.get("mission") or {}).get("id"),
        "mission_version": doc.get("mission_version"),
        "transaction_id": doc.get("transaction_id"),
        "state": doc.get("state"),
        "operational_status": doc.get("operational_status"),
        "roles": doc.get("roles"),
        "platform": {
            "is_actor": False,
            "engines": [
                "mission_runtime",
                "runtime_truth_engine",
                "governance_engine",
                "event_bus",
            ],
        },
    }
