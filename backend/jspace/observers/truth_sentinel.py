"""Truth Sentinel — false-green, stale, unknown, contradictory, unsupported states."""
from __future__ import annotations

from typing import Any, Dict, List

from backend.jspace.observers.base import ObserverBase, ObserverResult
from backend.jspace.truth_classes import TruthAssessment


class TruthSentinel(ObserverBase):
    name = "jspace_truth_sentinel"

    def observe(self, snapshot: Dict[str, Any]) -> ObserverResult:
        result = ObserverResult(observer=self.name)
        rt = snapshot.get("runtime") or {}
        ptr = rt.get("pointer") or {}
        locks: List[dict] = rt.get("active_locks") or []
        evidence_paths = []
        if rt.get("pointer_path"):
            evidence_paths.append(rt["pointer_path"])

        # 1) Runtime pointer publication
        if not ptr or not ptr.get("ledger_path"):
            a = self._assessment(
                subject="runtime_pointer",
                assessment=TruthAssessment.UNCONFIRMED,
                claimed_state="PUBLISHED",
                observed_state="MISSING_OR_EMPTY",
                evidence=evidence_paths or ["coordination/council/active_runtime_source.json"],
                confidence=0.95,
                recommended_action="WITHHOLD_PROMOTION",
                detail="No active_runtime_source pointer; wall/runtime claims cannot be confirmed live.",
            )
            result.assessments.append(a)
            result.alerts.append(self._alert(
                severity="HIGH",
                title="Runtime pointer unpublished",
                subject="runtime_pointer",
                assessment=a.assessment.value,
                recommended_action=a.recommended_action,
                evidence=a.evidence,
            ))
        else:
            result.assessments.append(self._assessment(
                subject="runtime_pointer",
                assessment=TruthAssessment.CONFIRMED_LIVE,
                claimed_state="PUBLISHED",
                observed_state=f"instance={ptr.get('scheduler_instance_id')}",
                evidence=evidence_paths + [str(ptr.get("ledger_path"))],
                confidence=0.9,
                recommended_action="NONE",
                detail="Runtime pointer present with ledger_path and instance id.",
            ))

        # 2) Active locks must carry authority binding when claimed ACTIVE/RUNNING
        unbound = []
        for lk in locks:
            status = str(lk.get("status") or "").upper()
            lease_status = str(lk.get("lease_status") or "").upper()
            activeish = status in ("ACTIVE", "ACQUIRED", "RUNNING") or lease_status == "RUNNING"
            if not activeish:
                continue
            if not lk.get("authority_decision_id"):
                unbound.append(lk.get("task_id") or lk.get("lease_id") or "unknown")

        if locks and unbound:
            a = self._assessment(
                subject="active_leases_authority",
                assessment=TruthAssessment.CONTRADICTED,
                claimed_state="AUTHORITY_BOUND",
                observed_state=f"UNBOUND_ACTIVE={len(unbound)}",
                evidence=evidence_paths + ["coordination/leases/*.lock"],
                confidence=0.99,
                recommended_action="WITHHOLD_PROMOTION",
                detail=f"Active leases missing authority_decision_id: {unbound[:8]}",
            )
            result.assessments.append(a)
            result.alerts.append(self._alert(
                severity="CRITICAL",
                title="Active work without authority binding",
                subject="active_leases_authority",
                assessment=a.assessment.value,
                recommended_action=a.recommended_action,
                evidence=a.evidence,
            ))
        elif locks:
            result.assessments.append(self._assessment(
                subject="active_leases_authority",
                assessment=TruthAssessment.CONFIRMED_LIVE,
                claimed_state="AUTHORITY_BOUND",
                observed_state=f"BOUND_ACTIVE={len(locks)}",
                evidence=["coordination/leases/*.lock"],
                confidence=0.9,
                recommended_action="NONE",
                detail="All active lock records carry authority_decision_id.",
            ))
        else:
            result.assessments.append(self._assessment(
                subject="active_leases_authority",
                assessment=TruthAssessment.CONFIRMED_LIVE,
                claimed_state="IDLE",
                observed_state="NO_ACTIVE_LOCKS",
                evidence=["coordination/leases"],
                confidence=0.85,
                recommended_action="NONE",
                detail="No active lease locks; authority panel may be EMPTY_OK if wall agrees.",
            ))

        # 3) Instance consistency: locks vs pointer
        inst = ptr.get("scheduler_instance_id")
        foreign = [
            lk for lk in locks
            if inst and lk.get("scheduler_instance_id") and lk.get("scheduler_instance_id") != inst
        ]
        if foreign:
            a = self._assessment(
                subject="scheduler_instance_consistency",
                assessment=TruthAssessment.CONTRADICTED,
                claimed_state=str(inst),
                observed_state=f"FOREIGN_LOCKS={len(foreign)}",
                evidence=evidence_paths + ["coordination/leases/*.lock"],
                confidence=0.97,
                recommended_action="RELEASE_ORPHAN_LEASES",
                detail="Active locks reference a different scheduler_instance_id than the runtime pointer.",
            )
            result.assessments.append(a)
            result.alerts.append(self._alert(
                severity="HIGH",
                title="Cross-instance lease pollution",
                subject="scheduler_instance_consistency",
                assessment=a.assessment.value,
                recommended_action=a.recommended_action,
                evidence=a.evidence,
            ))

        return result
