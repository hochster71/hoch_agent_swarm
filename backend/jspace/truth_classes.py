"""HELM truth classes used by HJOS assessments.

No monitoring agent emits GO. Assessments resolve to one of these classes.
"""
from __future__ import annotations

from enum import Enum


class TruthAssessment(str, Enum):
    CONFIRMED_LIVE = "CONFIRMED_LIVE"
    UNCONFIRMED = "UNCONFIRMED"
    STALE = "STALE"
    UNVERIFIED = "UNVERIFIED"
    UNKNOWN = "UNKNOWN"
    BLOCKED = "BLOCKED"
    CONTRADICTED = "CONTRADICTED"


# Severity for meta-reconcile (higher = worse for overall health)
ASSESSMENT_SEVERITY = {
    TruthAssessment.CONFIRMED_LIVE: 0,
    TruthAssessment.UNCONFIRMED: 1,
    TruthAssessment.UNVERIFIED: 2,
    TruthAssessment.STALE: 3,
    TruthAssessment.UNKNOWN: 4,
    TruthAssessment.BLOCKED: 5,
    TruthAssessment.CONTRADICTED: 6,
}
