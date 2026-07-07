"""Pydantic request/response models for the Apple Calendar adapter.

Requires ``pydantic``. The FastAPI app imports these; the pure-logic modules
(``redaction``, ``ledger``) and the security-gate functions in ``app`` do NOT,
so the offline security/redaction test suites run without pydantic installed.

Validation of interest:
  * ``EventCreateRequest`` requires ``title``, ``start``, ``end``,
    ``calendar_name``; ``description`` is optional.
  * ``start`` must be strictly earlier than ``end`` (parsed with
    ``datetime.fromisoformat``).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


def _parse_iso(value: str) -> datetime:
    """Strict ISO-8601 parse. Raises ValueError on bad input (fail closed)."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("datetime must be a non-empty ISO-8601 string")
    return datetime.fromisoformat(value)


class EventCreateRequest(BaseModel):
    """Payload to create (or dry-run) a calendar event."""

    title: str = Field(..., min_length=1, description="Event title / summary.")
    start: str = Field(..., description="ISO-8601 start datetime.")
    end: str = Field(..., description="ISO-8601 end datetime.")
    calendar_name: str = Field(..., min_length=1, description="Target calendar.")
    description: Optional[str] = Field(
        default=None,
        description="Optional body. Redacted in responses unless approved.",
    )

    @field_validator("start", "end")
    @classmethod
    def _validate_iso(cls, v: str) -> str:
        _parse_iso(v)  # raises if not valid ISO-8601
        return v

    @model_validator(mode="after")
    def _validate_range(self) -> "EventCreateRequest":
        start_dt = _parse_iso(self.start)
        end_dt = _parse_iso(self.end)
        if not start_dt < end_dt:
            raise ValueError("start must be strictly earlier than end")
        return self


class EventCreateApproved(EventCreateRequest):
    """Create request that additionally carries approval evidence.

    A write is only accepted when the adapter is in ``read_write`` mode AND one
    of these is present/true. Presence is necessary but not sufficient — the
    mode gate is enforced server-side (see ``app.evaluate_write_gate``).
    """

    approval_token: Optional[str] = Field(
        default=None, description="Opaque approval token from the approver."
    )
    approved: bool = Field(
        default=False, description="Explicit human approval flag."
    )
    requested_by: Optional[str] = Field(
        default=None, description="Identity of the requesting agent/human."
    )


class DryRunResponse(BaseModel):
    """Result of a dry-run: the proposed ICS, never written to Apple."""

    proposed: bool = True
    written: bool = False
    calendar_name: str
    ics: str
    note: str = "dry-run only — nothing was written to Apple Calendar"
