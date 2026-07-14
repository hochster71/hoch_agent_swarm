"""Meta-Observer — reconcile specialist findings into one governed health view."""
from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from backend.jspace.observers.base import ObserverBase, ObserverResult
from backend.jspace.schema import JSpaceAssessment, JSpaceHealth
from backend.jspace.truth_classes import ASSESSMENT_SEVERITY, TruthAssessment


class MetaObserver(ObserverBase):
    name = "jspace_meta_observer"

    def observe(self, snapshot: Dict[str, Any]) -> ObserverResult:
        # Meta operates on specialist results passed via snapshot["_specialist_results"]
        raise RuntimeError("Use MetaObserver.reconcile() instead of observe()")

    def reconcile(
        self,
        specialist_results: List[ObserverResult],
    ) -> tuple[JSpaceHealth, ObserverResult]:
        assessments: List[JSpaceAssessment] = []
        alerts = []
        counts: Counter = Counter()

        for res in specialist_results:
            for a in res.assessments:
                assessments.append(a)
                counts[a.assessment.value] += 1
            alerts.extend(res.alerts)

        worst = TruthAssessment.CONFIRMED_LIVE
        worst_rows: List[dict] = []
        for a in assessments:
            if ASSESSMENT_SEVERITY[a.assessment] > ASSESSMENT_SEVERITY[worst]:
                worst = a.assessment
            if a.assessment in (
                TruthAssessment.CONTRADICTED,
                TruthAssessment.BLOCKED,
                TruthAssessment.STALE,
            ):
                worst_rows.append({
                    "observation_id": a.observation_id,
                    "subject": a.subject,
                    "observer": a.observer,
                    "assessment": a.assessment.value,
                    "recommended_action": a.recommended_action,
                    "detail": a.detail[:240],
                })

        # Cap worst findings list
        worst_rows = sorted(
            worst_rows,
            key=lambda r: ASSESSMENT_SEVERITY[TruthAssessment(r["assessment"])],
            reverse=True,
        )[:12]

        if worst in (TruthAssessment.CONTRADICTED, TruthAssessment.BLOCKED):
            action = "WITHHOLD_PROMOTION"
        elif worst in (TruthAssessment.STALE, TruthAssessment.UNVERIFIED):
            action = "INVESTIGATE_BEFORE_PROMOTION"
        elif worst == TruthAssessment.UNKNOWN:
            action = "REQUIRE_EVIDENCE"
        else:
            action = "NONE"

        health = JSpaceHealth(
            overall=worst,
            cycle_id=self.cycle_id,
            observer_counts=dict(counts),
            open_alerts=len(alerts),
            worst_findings=worst_rows,
            recommended_action=action,
            state_mutated=False,
        )

        meta_result = ObserverResult(observer=self.name)
        meta_result.assessments.append(self._assessment(
            subject="helm_jspace_health",
            assessment=worst,
            claimed_state="OPERATIONAL",
            observed_state=worst.value,
            evidence=["coordination/jspace/assessments.jsonl"],
            confidence=0.9,
            recommended_action=action,
            detail=(
                f"Reconciled {len(assessments)} specialist assessments; "
                f"alerts={len(alerts)}; promotion_authority=NONE."
            ),
        ))
        # Surface only high/critical alerts at meta layer (already collected)
        meta_result.alerts = [
            al for al in alerts if al.severity in ("HIGH", "CRITICAL")
        ]
        return health, meta_result
