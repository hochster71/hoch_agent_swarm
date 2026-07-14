"""Evidence Auditor — claims vs files, hashes, ledgers, provenance."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from backend.jspace.observers.base import ObserverBase, ObserverResult
from backend.jspace.truth_classes import TruthAssessment

ROOT = Path(__file__).resolve().parents[3]


class EvidenceAuditor(ObserverBase):
    name = "jspace_evidence_auditor"

    def observe(self, snapshot: Dict[str, Any]) -> ObserverResult:
        result = ObserverResult(observer=self.name)
        rt = snapshot.get("runtime") or {}
        ptr = rt.get("pointer") or {}
        auth = snapshot.get("authority") or {}

        # Pointer ledger must exist on disk
        ledger = ptr.get("ledger_path")
        if ledger:
            p = Path(ledger)
            if p.exists():
                result.assessments.append(self._assessment(
                    subject="canonical_lease_ledger",
                    assessment=TruthAssessment.CONFIRMED_LIVE,
                    claimed_state="EXISTS",
                    observed_state=f"bytes={p.stat().st_size}",
                    evidence=[str(ledger)],
                    confidence=0.95,
                    recommended_action="NONE",
                    detail="Declared lease ledger path exists.",
                ))
            else:
                a = self._assessment(
                    subject="canonical_lease_ledger",
                    assessment=TruthAssessment.CONTRADICTED,
                    claimed_state="EXISTS",
                    observed_state="MISSING_ON_DISK",
                    evidence=[str(ledger), rt.get("pointer_path") or "active_runtime_source.json"],
                    confidence=0.99,
                    recommended_action="WITHHOLD_PROMOTION",
                    detail="Runtime pointer declares a ledger path that does not exist.",
                )
                result.assessments.append(a)
                result.alerts.append(self._alert(
                    severity="CRITICAL",
                    title="Declared ledger missing on disk",
                    subject="canonical_lease_ledger",
                    assessment=a.assessment.value,
                    recommended_action=a.recommended_action,
                    evidence=a.evidence,
                ))
        else:
            result.assessments.append(self._assessment(
                subject="canonical_lease_ledger",
                assessment=TruthAssessment.UNKNOWN,
                claimed_state="DECLARED",
                observed_state="NO_POINTER_LEDGER",
                evidence=["coordination/council/active_runtime_source.json"],
                confidence=0.9,
                recommended_action="PUBLISH_RUNTIME_POINTER",
                detail="Cannot audit lease ledger without a published pointer.",
            ))

        # Authority binding rows must not be empty of decision digests when present
        rows: List[dict] = auth.get("authority_binding_tail") or []
        incomplete = [
            r for r in rows
            if r.get("authority_decision_id") and not r.get("decision_digest")
        ]
        if rows and incomplete:
            a = self._assessment(
                subject="authority_binding_completeness",
                assessment=TruthAssessment.UNVERIFIED,
                claimed_state="DIGEST_BOUND",
                observed_state=f"incomplete={len(incomplete)}/{len(rows)}",
                evidence=list(filter(None, (auth.get("paths") or {}).values())),
                confidence=0.85,
                recommended_action="REJECT_INCOMPLETE_BINDINGS",
                detail="Some authority rows have decision id without decision_digest.",
            )
            result.assessments.append(a)
        elif rows:
            result.assessments.append(self._assessment(
                subject="authority_binding_completeness",
                assessment=TruthAssessment.CONFIRMED_LIVE,
                claimed_state="DIGEST_BOUND",
                observed_state=f"rows={len(rows)}",
                evidence=list(filter(None, (auth.get("paths") or {}).values())),
                confidence=0.85,
                recommended_action="NONE",
                detail="Sampled authority binding rows include digests where decision ids exist.",
            ))
        else:
            result.assessments.append(self._assessment(
                subject="authority_binding_completeness",
                assessment=TruthAssessment.UNCONFIRMED,
                claimed_state="PRESENT",
                observed_state="NO_ROWS_SAMPLED",
                evidence=["coordination/founder/authority_binding_ledger.jsonl"],
                confidence=0.6,
                recommended_action="NONE",
                detail="No authority binding rows in sample window.",
            ))

        # Active lock claims of artifact/path existence (if path fields present)
        for lk in (rt.get("active_locks") or [])[:10]:
            art = lk.get("artifact_path")
            if not art:
                continue
            ap = Path(art)
            if not ap.is_absolute():
                ap = ROOT / art
            if not ap.exists():
                a = self._assessment(
                    subject=lk.get("task_id") or "artifact",
                    assessment=TruthAssessment.CONTRADICTED,
                    claimed_state="ARTIFACT_EXISTS",
                    observed_state="MISSING",
                    evidence=[str(art)],
                    confidence=0.95,
                    recommended_action="WITHHOLD_PROMOTION",
                    detail="Lock/task claims artifact path that is not on disk.",
                )
                result.assessments.append(a)

        return result
