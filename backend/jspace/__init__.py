"""HELM J-SPACE Observability Swarm (HJOS).

Independently observe HELM agent activity, verify runtime and evidence truth,
detect contradictions and unsafe behavior, and emit fail-closed recommendations
without promoting, executing, or rewriting authoritative HELM state.

default_mode: READ_ONLY
promotion_authority: NONE
"""
from __future__ import annotations

from backend.jspace.charter import HJOS_CHARTER, ObserverMode
from backend.jspace.runner import run_hjos_cycle
from backend.jspace.truth_classes import TruthAssessment

__all__ = [
    "HJOS_CHARTER",
    "ObserverMode",
    "TruthAssessment",
    "run_hjos_cycle",
]
