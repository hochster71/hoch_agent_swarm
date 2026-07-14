"""J-SPACE event and assessment schemas.

Events describe observed HELM activity. Assessments are signed (digest-bound)
observer conclusions — never promotions.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from backend.jspace.truth_classes import TruthAssessment

SCHEMA_EVENT = "JSPACE_EVENT_v1"
SCHEMA_ASSESSMENT = "JSPACE_ASSESSMENT_v1"
SCHEMA_ALERT = "JSPACE_ALERT_v1"
SCHEMA_HEALTH = "JSPACE_HEALTH_v1"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _digest(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def new_id(prefix: str) -> str:
    stamp = time.strftime("%Y%m%d", time.gmtime())
    return f"{prefix}-{stamp}-{uuid.uuid4().hex[:6].upper()}"


@dataclass
class JSpaceEvent:
    """One observed activity unit on the J-SPACE bus."""

    event_type: str
    source: str
    subject: str
    payload: Dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: new_id("JEVT"))
    observed_at: str = field(default_factory=_now)
    schema: str = SCHEMA_EVENT

    def to_dict(self) -> dict:
        d = asdict(self)
        d["event_digest"] = _digest({k: v for k, v in d.items() if k != "event_digest"})
        return d


@dataclass
class JSpaceAssessment:
    """Fail-closed observer assessment. Never a GO/promotion."""

    subject: str
    observer: str
    assessment: TruthAssessment
    claimed_state: Optional[str] = None
    observed_state: Optional[str] = None
    evidence: List[str] = field(default_factory=list)
    confidence: float = 0.5
    recommended_action: str = "NONE"
    detail: str = ""
    observation_id: str = field(default_factory=lambda: new_id("JOBS"))
    observed_at: str = field(default_factory=_now)
    state_mutated: bool = False
    schema: str = SCHEMA_ASSESSMENT
    cycle_id: Optional[str] = None

    def __post_init__(self) -> None:
        if isinstance(self.assessment, str):
            self.assessment = TruthAssessment(self.assessment)
        if self.state_mutated:
            raise PermissionError("HJOS assessments must set state_mutated=false")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("confidence must be in [0,1]")

    def to_dict(self) -> dict:
        d = {
            "schema": self.schema,
            "observation_id": self.observation_id,
            "subject": self.subject,
            "observer": self.observer,
            "assessment": self.assessment.value,
            "claimed_state": self.claimed_state,
            "observed_state": self.observed_state,
            "evidence": list(self.evidence),
            "confidence": float(self.confidence),
            "recommended_action": self.recommended_action,
            "detail": self.detail,
            "state_mutated": False,
            "observed_at": self.observed_at,
            "cycle_id": self.cycle_id,
        }
        d["assessment_digest"] = _digest(d)
        return d


@dataclass
class JSpaceAlert:
    """Alert for founder/dashboard surfaces. Not an execution command."""

    severity: str  # INFO | WARN | HIGH | CRITICAL
    title: str
    subject: str
    observer: str
    assessment: str
    recommended_action: str
    evidence: List[str] = field(default_factory=list)
    alert_id: str = field(default_factory=lambda: new_id("JALT"))
    observed_at: str = field(default_factory=_now)
    schema: str = SCHEMA_ALERT
    cycle_id: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["alert_digest"] = _digest({k: v for k, v in d.items() if k != "alert_digest"})
        return d


@dataclass
class JSpaceHealth:
    """Meta-observer governed HELM health assessment (one per cycle)."""

    overall: TruthAssessment
    cycle_id: str
    observer_counts: Dict[str, int]
    open_alerts: int
    worst_findings: List[dict]
    recommended_action: str
    state_mutated: bool = False
    observed_at: str = field(default_factory=_now)
    schema: str = SCHEMA_HEALTH
    promotion_authority: str = "NONE"

    def to_dict(self) -> dict:
        if self.state_mutated:
            raise PermissionError("health assessment cannot mutate state")
        d = {
            "schema": self.schema,
            "overall": self.overall.value if isinstance(self.overall, TruthAssessment) else self.overall,
            "cycle_id": self.cycle_id,
            "observer_counts": self.observer_counts,
            "open_alerts": self.open_alerts,
            "worst_findings": self.worst_findings,
            "recommended_action": self.recommended_action,
            "state_mutated": False,
            "promotion_authority": "NONE",
            "observed_at": self.observed_at,
        }
        d["health_digest"] = _digest(d)
        return d
