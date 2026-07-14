"""Flow Sentinel — queues, leases, locks, retries, deadlocks, starvation, orphans."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List

from backend.jspace.observers.base import ObserverBase, ObserverResult
from backend.jspace.truth_classes import TruthAssessment


def _parse_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


class FlowSentinel(ObserverBase):
    name = "jspace_flow_sentinel"

    def observe(self, snapshot: Dict[str, Any]) -> ObserverResult:
        result = ObserverResult(observer=self.name)
        rt = snapshot.get("runtime") or {}
        locks: List[dict] = rt.get("active_locks") or []
        events: List[dict] = rt.get("lease_events_tail") or []
        now = datetime.now(timezone.utc)

        # Expired but still ACTIVE locks
        expired_active = []
        for lk in locks:
            exp = _parse_ts(lk.get("expires_at"))
            status = str(lk.get("status") or "").upper()
            if exp and exp < now and status in ("ACTIVE", "ACQUIRED", "RUNNING"):
                expired_active.append(lk.get("task_id") or lk.get("lease_id"))

        if expired_active:
            a = self._assessment(
                subject="lease_expiry",
                assessment=TruthAssessment.CONTRADICTED,
                claimed_state="ACTIVE",
                observed_state="LEASE_EXPIRED",
                evidence=["coordination/leases/*.lock"],
                confidence=0.99,
                recommended_action="RELEASE_EXPIRED_LEASES",
                detail=f"Locks past expires_at still ACTIVE: {expired_active[:8]}",
            )
            result.assessments.append(a)
            result.alerts.append(self._alert(
                severity="HIGH",
                title="Expired leases still held",
                subject="lease_expiry",
                assessment=a.assessment.value,
                recommended_action=a.recommended_action,
                evidence=a.evidence,
            ))
        else:
            result.assessments.append(self._assessment(
                subject="lease_expiry",
                assessment=TruthAssessment.CONFIRMED_LIVE,
                claimed_state="WITHIN_TTL",
                observed_state=f"active_locks={len(locks)}",
                evidence=["coordination/leases/*.lock"],
                confidence=0.85,
                recommended_action="NONE",
                detail="No active locks past expires_at.",
            ))

        # Acquire/release balance on tail
        acq = sum(1 for e in events if e.get("status") == "ACQUIRED")
        rel = sum(1 for e in events if e.get("status") == "RELEASED")
        # open estimate from events alone (tail-local)
        by_lease: Dict[str, str] = {}
        for e in events:
            lid = e.get("lease_id")
            if lid and e.get("status"):
                by_lease[lid] = e["status"]
        open_est = sum(1 for s in by_lease.values() if s not in ("RELEASED", "EXPIRED", "COMPLETED"))
        leak_hint = open_est > max(len(locks) + 2, 4) and acq > rel + 4

        if leak_hint:
            a = self._assessment(
                subject="lease_balance",
                assessment=TruthAssessment.UNVERIFIED,
                claimed_state="BALANCED",
                observed_state=f"acq={acq} rel={rel} open_est={open_est} locks={len(locks)}",
                evidence=["task_lease_ledger.jsonl", "coordination/leases"],
                confidence=0.7,
                recommended_action="INVESTIGATE_LEASE_LEAK",
                detail="Tail acquire/release skew suggests possible lease leak (not yet terminal).",
            )
            result.assessments.append(a)
            result.alerts.append(self._alert(
                severity="WARN",
                title="Possible lease leak skew",
                subject="lease_balance",
                assessment=a.assessment.value,
                recommended_action=a.recommended_action,
                evidence=a.evidence,
            ))
        else:
            result.assessments.append(self._assessment(
                subject="lease_balance",
                assessment=TruthAssessment.CONFIRMED_LIVE,
                claimed_state="BALANCED",
                observed_state=f"acq={acq} rel={rel} locks={len(locks)}",
                evidence=["task_lease_ledger.jsonl"],
                confidence=0.8,
                recommended_action="NONE",
                detail="Lease tail balance does not indicate a leak.",
            ))

        # Capacity pressure: many locks
        if len(locks) > 8:
            result.assessments.append(self._assessment(
                subject="concurrency_pressure",
                assessment=TruthAssessment.BLOCKED,
                claimed_state="WITHIN_CAPACITY",
                observed_state=f"active_locks={len(locks)}",
                evidence=["coordination/leases"],
                confidence=0.75,
                recommended_action="THROTTLE_OR_INVESTIGATE",
                detail="Unusually high number of simultaneous lease locks.",
            ))

        return result
