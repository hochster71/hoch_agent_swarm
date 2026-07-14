"""Read-only observer base class."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List

from backend.jspace.charter import HJOS_CHARTER
from backend.jspace.schema import JSpaceAlert, JSpaceAssessment


@dataclass
class ObserverResult:
    observer: str
    assessments: List[JSpaceAssessment] = field(default_factory=list)
    alerts: List[JSpaceAlert] = field(default_factory=list)
    events_emitted: int = 0


class ObserverBase(ABC):
    name: str = "jspace_observer"

    def __init__(self, cycle_id: str) -> None:
        self.cycle_id = cycle_id
        self.charter = HJOS_CHARTER

    @abstractmethod
    def observe(self, snapshot: Dict[str, Any]) -> ObserverResult:
        """Inspect snapshot; return assessments/alerts. Must not mutate HELM state."""

    def _assessment(self, **kwargs) -> JSpaceAssessment:
        kwargs.setdefault("observer", self.name)
        kwargs.setdefault("cycle_id", self.cycle_id)
        kwargs["state_mutated"] = False
        a = JSpaceAssessment(**kwargs)
        self.charter.assert_read_only(state_mutated=a.state_mutated)
        return a

    def _alert(
        self,
        *,
        severity: str,
        title: str,
        subject: str,
        assessment: str,
        recommended_action: str,
        evidence: List[str] | None = None,
    ) -> JSpaceAlert:
        return JSpaceAlert(
            severity=severity,
            title=title,
            subject=subject,
            observer=self.name,
            assessment=assessment,
            recommended_action=recommended_action,
            evidence=list(evidence or []),
            cycle_id=self.cycle_id,
        )
