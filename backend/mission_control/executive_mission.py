"""Executive Mission helpers — thin facade over helm_runtime (platform engines).

Legacy import path kept for compatibility. Prefer:
  backend.helm_runtime.transaction.commit_proposal
  backend.helm_runtime.mission_runtime.load_mission
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.helm_runtime.governance_engine import (
    normalize_role,
    role_may_write,
    validate_proposal,
)
from backend.helm_runtime.mission_runtime import load_mission as load_executive_mission
from backend.helm_runtime.mission_runtime import mission_projection_hint
from backend.helm_runtime.transaction import commit_proposal

ROOT = Path(__file__).resolve().parents[2]
EXEC_PATH = ROOT / "coordination" / "goal" / "executive_mission.json"
OWNERSHIP_PATH = ROOT / "coordination" / "governance" / "field_ownership.json"


def load_ownership(path: Path = OWNERSHIP_PATH) -> Dict[str, Any]:
    import json

    if not path.exists():
        return {"roles": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def assert_role_may_write(role: str, field_path: str, ownership: Optional[Dict[str, Any]] = None) -> bool:
    return role_may_write(role, field_path, ownership)


def record_write(
    role: str,
    fields: List[str],
    *,
    actor: Optional[str] = None,
    artifact: str = "coordination/goal/executive_mission.json",
    correlation_id: Optional[str] = None,
    note: str = "",
    path: Path = EXEC_PATH,
    enforce_ownership: bool = True,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Commit a patch via MissionTransaction (version bump + event)."""
    # last_writes is appended by transaction; map fields to no-op status touch if empty patch needed
    patch = {f: kwargs.get("values", {}).get(f, "TOUCHED") for f in fields if f != "last_writes"}
    if not patch:
        patch = {"mission.implementation_notes": note or "record_write"}
    result = commit_proposal(
        role,
        patch,
        actor=actor,
        correlation_id=correlation_id,
        note=note,
        path=path,
        recompute_truth=kwargs.get("recompute_truth", False),
        founder_token_present=kwargs.get("founder_token_present", False),
    )
    if not result.get("ok"):
        raise PermissionError(result.get("error") or result.get("errors") or result)
    return result


def mission_summary(path: Path = EXEC_PATH) -> Dict[str, Any]:
    doc = load_executive_mission(path)
    return {
        "schema": doc.get("schema"),
        "mission_id": (doc.get("mission") or {}).get("id"),
        "mission_version": doc.get("mission_version"),
        "transaction_id": doc.get("transaction_id"),
        "state": doc.get("state"),
        "operational_status": doc.get("operational_status"),
        "roles": doc.get("roles"),
        "platform": doc.get("platform"),
        "assurance": {
            "status": (doc.get("assurance") or {}).get("status"),
            "verdict": (doc.get("assurance") or {}).get("auditor_verdict"),
            "deployment_recommendation": (doc.get("assurance") or {}).get("deployment_recommendation"),
        },
        "projection_hint": mission_projection_hint(path),
        "charter": doc.get("charter"),
    }
