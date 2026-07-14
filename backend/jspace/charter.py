"""HJOS charter — fixed operational constraints.

Monitors observe, validate, correlate, and escalate.
They must not become another autonomous command layer competing with HELM.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import FrozenSet, Tuple


class ObserverMode(str, Enum):
    READ_ONLY = "READ_ONLY"


@dataclass(frozen=True)
class HJOSCharter:
    name: str = "HELM J-SPACE Observability Swarm"
    short_name: str = "HJOS"
    mission: str = (
        "Independently observe all HELM agent activity, verify runtime and "
        "evidence truth, detect contradictions and unsafe behavior, and provide "
        "fail-closed recommendations without independently promoting, executing, "
        "or rewriting authoritative HELM state."
    )
    default_mode: ObserverMode = ObserverMode.READ_ONLY
    state_mutation: str = "PROHIBITED"
    task_execution: str = "PROHIBITED"
    evidence_creation: str = "ALLOWED"
    alert_creation: str = "ALLOWED"
    quarantine_request: str = "ALLOWED"
    promotion_authority: str = "NONE"
    # Automatic quarantine is gated until a proven read-only burn-in.
    automatic_quarantine_enabled: bool = False
    automatic_quarantine_permitted_only_for: FrozenSet[str] = field(
        default_factory=lambda: frozenset({
            "secret_exposure",
            "destructive_action",
            "founder_gate_bypass",
            "evidence_tampering",
        })
    )
    observers: Tuple[str, ...] = (
        "jspace_truth_sentinel",
        "jspace_flow_sentinel",
        "jspace_evidence_auditor",
        "jspace_security_sentinel",
        "jspace_performance_analyst",
        "jspace_meta_observer",
    )

    def assert_read_only(self, *, state_mutated: bool) -> None:
        if state_mutated:
            raise PermissionError(
                "HJOS charter violation: state_mutation is PROHIBITED "
                f"(mode={self.default_mode.value})"
            )


HJOS_CHARTER = HJOSCharter()
