"""HJOS specialist observers (read-only)."""
from __future__ import annotations

from backend.jspace.observers.base import ObserverBase, ObserverResult
from backend.jspace.observers.evidence_auditor import EvidenceAuditor
from backend.jspace.observers.flow_sentinel import FlowSentinel
from backend.jspace.observers.meta_observer import MetaObserver
from backend.jspace.observers.performance_analyst import PerformanceAnalyst
from backend.jspace.observers.security_sentinel import SecuritySentinel
from backend.jspace.observers.truth_sentinel import TruthSentinel

SPECIALISTS = (
    TruthSentinel,
    FlowSentinel,
    EvidenceAuditor,
    SecuritySentinel,
    PerformanceAnalyst,
)

__all__ = [
    "ObserverBase",
    "ObserverResult",
    "TruthSentinel",
    "FlowSentinel",
    "EvidenceAuditor",
    "SecuritySentinel",
    "PerformanceAnalyst",
    "MetaObserver",
    "SPECIALISTS",
]
