"""Canonical task-state semantics. ONE enum. Illegal states are rejected at INGESTION,
not laundered in the frontend.

Grok audit F-2 / F-5: values like `AgentHASF`, `IDEA` and `LEASE` were reaching the API and
the PERT wall as if they were task statuses.
  * AgentHASF is an ASSIGNED AGENT, not a status.
  * LEASE is a lifecycle event / lease state, not a status.
  * IDEA is an intake stage -- it is NOT proof of completed work.
And `COMPLETE` was being used for states that do not represent completed work.
"""
from __future__ import annotations

from enum import Enum
from typing import Any


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    LEASED = "LEASED"
    RUNNING = "RUNNING"
    VERIFYING = "VERIFYING"
    RETRYABLE = "RETRYABLE"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    COMPLETE = "COMPLETE"
    UNKNOWN = "UNKNOWN"
    STALE = "STALE"


VALID_TASK_STATUSES = frozenset(s.value for s in TaskStatus)

# Legacy values mapped ONLY where the meaning is unambiguous. We never guess.
_LEGACY_MAP = {
    "COMPLETED": TaskStatus.COMPLETE.value,
    "RETIRED": TaskStatus.STALE.value,
    "IN_PROGRESS": TaskStatus.RUNNING.value,
}

# The audit's exact examples: these must NEVER be treated as a status.
NOT_A_STATUS = ("IDEA", "LEASE")


class InvalidTaskStatus(ValueError):
    """Typed error. An illegal status must fail loudly, not appear on the wall."""

    def __init__(self, value: Any, reason: str = ""):
        self.code = "INVALID_TASK_STATUS"
        self.value = value
        super().__init__(f"INVALID_TASK_STATUS: {value!r} {reason}".strip())


def is_agent_label(value: Any) -> bool:
    """`AgentHASF` etc. belong in assigned_agent, never in status."""
    return isinstance(value, str) and value.strip().lower().startswith("agent")


def validate_status(value: Any) -> str:
    """Return a canonical status, or raise InvalidTaskStatus. NEVER silently coerce."""
    if value is None:
        raise InvalidTaskStatus(value, "(null)")
    v = str(value).strip()
    if not v:
        raise InvalidTaskStatus(value, "(empty)")
    up = v.upper()

    if is_agent_label(v):
        raise InvalidTaskStatus(value, "- this is an assigned_agent, not a status")
    if up in NOT_A_STATUS:
        raise InvalidTaskStatus(
            value, "- IDEA is an intake stage and LEASE is a lifecycle event; neither is a status")
    if up in VALID_TASK_STATUSES:
        return up
    if up in _LEGACY_MAP:
        return _LEGACY_MAP[up]
    raise InvalidTaskStatus(value, "- not in the canonical enum")


def coerce_for_display(value: Any) -> tuple[str, str | None]:
    """Read paths: (status, error). An illegal value renders UNKNOWN and carries the typed
    error. It is NEVER shown as a legitimate state, and NEVER as COMPLETE."""
    try:
        return validate_status(value), None
    except InvalidTaskStatus as e:
        return TaskStatus.UNKNOWN.value, str(e)


# ---- COMPLETE is earned, never asserted -------------------------------------------------
COMPLETION_REQUIREMENTS = (
    "execution_finished", "validator_passed", "artifact_exists",
    "evidence_fresh", "provenance_matches",
)


def may_be_complete(*, execution_finished: bool, validator_passed: bool,
                    artifact_exists: bool, evidence_fresh: bool,
                    provenance_matches: bool) -> tuple[bool, list[str]]:
    """A node may become COMPLETE ONLY when ALL five hold. Returns (ok, unmet)."""
    facts = dict(execution_finished=execution_finished, validator_passed=validator_passed,
                 artifact_exists=artifact_exists, evidence_fresh=evidence_fresh,
                 provenance_matches=provenance_matches)
    unmet = [k for k in COMPLETION_REQUIREMENTS if not facts[k]]
    return (not unmet), unmet


def resolve_status(*, raw: Any, execution_finished: bool = False, validator_passed: bool = False,
                   artifact_exists: bool = False, evidence_fresh: bool = False,
                   provenance_matches: bool = False) -> dict[str, Any]:
    """Authoritative resolution. A COMPLETE claim is DOWNGRADED unless it is earned."""
    status, err = coerce_for_display(raw)
    if status == TaskStatus.COMPLETE.value:
        ok, unmet = may_be_complete(
            execution_finished=execution_finished, validator_passed=validator_passed,
            artifact_exists=artifact_exists, evidence_fresh=evidence_fresh,
            provenance_matches=provenance_matches)
        if not ok:
            return {"status": TaskStatus.VERIFYING.value, "claimed": TaskStatus.COMPLETE.value,
                    "downgraded": True, "unmet_completion_requirements": unmet, "error": err}
    return {"status": status, "downgraded": False, "error": err}
