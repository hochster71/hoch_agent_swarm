"""Role Router — the single inbound door to HELM.

No model talks to another model. Every model (and the founder) talks to HELM
through this one entry point. A worker submits a *role-tagged, version-pinned
proposal*; the router validates the role, enforces optimistic concurrency, and
hands the proposal to the transaction engine (validate → authorize → commit →
event → recompute truth).

This is what makes the three frontier models interoperable workers over a
shared runtime instead of three separate conversations.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.helm_runtime.governance_engine import normalize_role
from backend.helm_runtime.mission_store import commit, current_version, read_mission
from backend.helm_runtime.provider_router import VALID_ROLES, resolve_worker
from backend.helm_runtime.transaction import EXEC_PATH

# Roles that may submit proposals through the bridge. Founder may too (for
# founder-gate fields) but must carry an explicit authorization token.
SUBMITTING_ROLES = ("founder",) + VALID_ROLES


def route_proposal(
    role: str,
    patch: Dict[str, Any],
    *,
    expected_parent_version: Optional[int] = None,
    actor: Optional[str] = None,
    evidence: Optional[List[str]] = None,
    note: str = "",
    correlation_id: Optional[str] = None,
    founder_token_present: bool = False,
    recompute_truth: bool = True,
    path: Path = EXEC_PATH,
) -> Dict[str, Any]:
    """Validate the role and commit the proposal under optimistic concurrency.

    Returns the transaction result. Distinct failure statuses:
      - ROLE_REJECTED     : unknown / non-actor role (e.g. "truth", "runtime")
      - MISSION_ABSENT    : no mission object to patch
      - CONFLICT          : version pinned by caller no longer current
      - FAILED            : validate/authorize denied (ownership / founder gate)
      - END               : committed
    """
    r = normalize_role(role)
    if r not in SUBMITTING_ROLES or r.startswith("INVALID_"):
        return {
            "ok": False,
            "status": "ROLE_REJECTED",
            "role": r,
            "error": "unknown or non-actor role; valid: founder, "
            "orchestrator, builder, auditor (Runtime/Truth are not actors)",
        }

    doc = read_mission(path)
    if doc.get("error") == "MISSION_ABSENT":
        return {"ok": False, "status": "MISSION_ABSENT", "path": str(path)}

    # If the caller pinned no version, pin it to current-on-read so the bridge
    # ALWAYS enforces compare-and-swap (a bare last-writer commit is not allowed
    # through the door).
    pinned = expected_parent_version
    if pinned is None:
        pinned = current_version(path)

    return commit(
        r,
        patch,
        expected_parent_version=pinned,
        actor=actor or (resolve_worker(r).get("display_name") if r in VALID_ROLES else "Michael"),
        evidence=evidence,
        note=note,
        correlation_id=correlation_id,
        founder_token_present=founder_token_present,
        recompute_truth=recompute_truth,
        path=path,
    )


def routing_status(path: Path = EXEC_PATH) -> Dict[str, Any]:
    """Projection for the bridge: what a worker needs to submit a proposal."""
    doc = read_mission(path)
    return {
        "engine": "role_router",
        "is_actor": False,
        "door": "route_proposal(role, patch, expected_parent_version=...)",
        "mission_present": doc.get("error") != "MISSION_ABSENT",
        "current_version": doc.get("mission_version"),
        "submitting_roles": list(SUBMITTING_ROLES),
        "occ": "compare_and_swap_required",
    }
