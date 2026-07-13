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


# ---- downgrade reason taxonomy ----------------------------------------------------------
class DowngradeReason(str, Enum):
    MISSING_VALIDATOR_EVIDENCE = "MISSING_VALIDATOR_EVIDENCE"
    MISSING_ARTIFACT = "MISSING_ARTIFACT"
    STALE_EVIDENCE = "STALE_EVIDENCE"
    PROVENANCE_MISMATCH = "PROVENANCE_MISMATCH"
    EXECUTION_NOT_COMPLETE = "EXECUTION_NOT_COMPLETE"


class RecordClass(str, Enum):
    GENUINE_INCOMPLETE = "GENUINE_INCOMPLETE"          # work really isn't done
    LEGACY_UNMIGRATED = "LEGACY_UNMIGRATED"            # done, but predates evidence capture
    MALFORMED = "MALFORMED"                            # illegal/garbage record
    STALE = "STALE"                                    # evidence too old to trust


# ---- COMPLETE is earned, never asserted -------------------------------------------------
COMPLETION_REQUIREMENTS = (
    "execution_status", "validator_status", "validator_evidence_id",
    "artifact_digest", "provenance_status", "freshness_status",
)


def completion_evidence(*, execution_status: Any = None, validator_status: Any = None,
                        validator_evidence_id: Any = None, artifact_digest: Any = None,
                        provenance_status: Any = None,
                        freshness_status: Any = None) -> tuple[bool, list[str]]:
    """COMPLETE requires EXPLICIT evidence for each field.

    CRITICAL: an artifact EXISTING does not prove a validator PASSED. An earlier version of
    this code inferred validator_passed from artifact_exists -- which manufactured a brand new
    false-positive path: any task that wrote a file would have been reported COMPLETE. The
    validator's own verdict must be presented, with an evidence id. Nothing is inferred.
    """
    reasons: list[str] = []
    if str(execution_status).upper() not in ("COMPLETED", "COMPLETE"):
        reasons.append(DowngradeReason.EXECUTION_NOT_COMPLETE.value)
    if str(validator_status).upper() != "PASS":
        reasons.append(DowngradeReason.MISSING_VALIDATOR_EVIDENCE.value)
    if not validator_evidence_id:
        if DowngradeReason.MISSING_VALIDATOR_EVIDENCE.value not in reasons:
            reasons.append(DowngradeReason.MISSING_VALIDATOR_EVIDENCE.value)
    if not artifact_digest:
        reasons.append(DowngradeReason.MISSING_ARTIFACT.value)
    if str(provenance_status).upper() != "PASS":
        reasons.append(DowngradeReason.PROVENANCE_MISMATCH.value)
    if str(freshness_status).upper() != "FRESH":
        reasons.append(DowngradeReason.STALE_EVIDENCE.value)
    return (not reasons), reasons


def classify_record(raw_status: Any, reasons: list[str]) -> str:
    """Distinguish genuine incomplete work from legacy/malformed/stale records."""
    up = str(raw_status).upper()
    if up not in VALID_TASK_STATUSES and up not in _LEGACY_MAP:
        return RecordClass.MALFORMED.value
    if DowngradeReason.STALE_EVIDENCE.value in reasons and len(reasons) == 1:
        return RecordClass.STALE.value
    # claimed complete, executed, but simply never captured evidence -> legacy, not a lie
    if up in ("COMPLETE", "COMPLETED") and \
            DowngradeReason.EXECUTION_NOT_COMPLETE.value not in reasons:
        return RecordClass.LEGACY_UNMIGRATED.value
    return RecordClass.GENUINE_INCOMPLETE.value


def resolve_status(*, raw: Any, **evidence: Any) -> dict[str, Any]:
    """Authoritative resolution. A COMPLETE claim is DOWNGRADED unless EXPLICIT evidence backs
    every requirement. Downgrades carry a typed reason list and a record classification."""
    status, err = coerce_for_display(raw)
    if status == TaskStatus.COMPLETE.value:
        ok, reasons = completion_evidence(**evidence)
        if not ok:
            return {"status": TaskStatus.VERIFYING.value,
                    "claimed": TaskStatus.COMPLETE.value,
                    "downgraded": True,
                    "downgrade_reasons": reasons,
                    "record_class": classify_record(raw, reasons),
                    "error": err}
    return {"status": status, "downgraded": False, "error": err,
            "record_class": (RecordClass.MALFORMED.value if err else None)}
