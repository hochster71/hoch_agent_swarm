"""Performance Analyst — latency proxies, cost, throughput, failure rates."""
from __future__ import annotations

from typing import Any, Dict, List

from backend.jspace.observers.base import ObserverBase, ObserverResult
from backend.jspace.truth_classes import TruthAssessment


class PerformanceAnalyst(ObserverBase):
    name = "jspace_performance_analyst"

    def observe(self, snapshot: Dict[str, Any]) -> ObserverResult:
        result = ObserverResult(observer=self.name)
        spend = snapshot.get("spend") or {}
        rows: List[dict] = spend.get("spend_tail") or []
        path = spend.get("path")

        if not rows:
            result.assessments.append(self._assessment(
                subject="spend_throughput",
                assessment=TruthAssessment.UNCONFIRMED,
                claimed_state="METERED",
                observed_state="NO_SPEND_ROWS",
                evidence=[path] if path else ["coordination/council/spend_ledger.jsonl"],
                confidence=0.6,
                recommended_action="NONE",
                detail="No recent spend ledger rows; cost throughput unconfirmed.",
            ))
            return result

        costs = []
        fails = 0
        for r in rows:
            c = r.get("cost_usd")
            if c is None:
                c = r.get("usd")
            if isinstance(c, (int, float)):
                costs.append(float(c))
            st = str(r.get("status") or r.get("result") or "").upper()
            if st in ("FAILED", "ERROR", "TIMEOUT"):
                fails += 1

        total = sum(costs) if costs else 0.0
        fail_rate = fails / max(len(rows), 1)
        observed = f"rows={len(rows)} cost_sum={total:.4f} fail_rate={fail_rate:.2f}"

        if fail_rate >= 0.5:
            a = self._assessment(
                subject="dispatch_failure_rate",
                assessment=TruthAssessment.BLOCKED,
                claimed_state="HEALTHY_THROUGHPUT",
                observed_state=observed,
                evidence=[path] if path else [],
                confidence=0.85,
                recommended_action="INVESTIGATE_ADAPTER_FAILURES",
                detail="Recent spend/dispatch sample shows high failure rate.",
            )
            result.assessments.append(a)
            result.alerts.append(self._alert(
                severity="WARN",
                title="High dispatch failure rate",
                subject="dispatch_failure_rate",
                assessment=a.assessment.value,
                recommended_action=a.recommended_action,
                evidence=a.evidence,
            ))
        else:
            result.assessments.append(self._assessment(
                subject="dispatch_failure_rate",
                assessment=TruthAssessment.CONFIRMED_LIVE,
                claimed_state="HEALTHY_THROUGHPUT",
                observed_state=observed,
                evidence=[path] if path else [],
                confidence=0.75,
                recommended_action="NONE",
                detail="Recent sample failure rate within acceptable band.",
            ))

        # Cost spike heuristic (absolute small window)
        if total > 25.0:
            result.assessments.append(self._assessment(
                subject="cost_window",
                assessment=TruthAssessment.UNVERIFIED,
                claimed_state="WITHIN_BUDGET",
                observed_state=f"cost_sum={total:.4f}",
                evidence=[path] if path else [],
                confidence=0.7,
                recommended_action="REVIEW_SPEND_GATE",
                detail="Elevated spend in sampled window; human budget review recommended.",
            ))

        # Runtime concurrency peak proxy
        locks = (snapshot.get("runtime") or {}).get("active_locks") or []
        result.assessments.append(self._assessment(
            subject="live_concurrency",
            assessment=TruthAssessment.CONFIRMED_LIVE,
            claimed_state="OBSERVED",
            observed_state=f"active_locks={len(locks)}",
            evidence=["coordination/leases"],
            confidence=0.8,
            recommended_action="NONE",
            detail="Live concurrency approximated by active lease lock count.",
        ))

        return result
