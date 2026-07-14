"""Security Sentinel — policy breaches, secret patterns, privilege drift."""
from __future__ import annotations

import re
from typing import Any, Dict, List

from backend.jspace.observers.base import ObserverBase, ObserverResult
from backend.jspace.truth_classes import TruthAssessment

# Coarse secret-shape detectors for *observed* text fields (not full DLP).
_SECRET_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "openai_like_key"),
    (re.compile(r"xai-[A-Za-z0-9]{20,}"), "xai_like_key"),
    (re.compile(r"-----BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY-----"), "private_key_pem"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "aws_access_key_id"),
]


class SecuritySentinel(ObserverBase):
    name = "jspace_security_sentinel"

    def observe(self, snapshot: Dict[str, Any]) -> ObserverResult:
        result = ObserverResult(observer=self.name)
        sec = snapshot.get("security") or {}
        posture = sec.get("control_posture") or {}
        paths = list(filter(None, (sec.get("paths") or {}).values()))

        if not posture or posture.get("_error"):
            result.assessments.append(self._assessment(
                subject="control_posture",
                assessment=TruthAssessment.UNKNOWN,
                claimed_state="AVAILABLE",
                observed_state="MISSING",
                evidence=paths or ["coordination/security/helm_control_posture.json"],
                confidence=0.8,
                recommended_action="RESTORE_CONTROL_POSTURE",
                detail="HELM control posture file missing or unreadable.",
            ))
        else:
            pct = posture.get("posture_percent")
            high = int(posture.get("high_findings") or 0)
            if high > 0 or (isinstance(pct, (int, float)) and pct < 80):
                a = self._assessment(
                    subject="control_posture",
                    assessment=TruthAssessment.BLOCKED,
                    claimed_state="WITHIN_POLICY",
                    observed_state=f"posture={pct} high_findings={high}",
                    evidence=paths,
                    confidence=0.9,
                    recommended_action="ESCALATE_FOUNDER_GATE",
                    detail="Control posture degraded or high findings open.",
                )
                result.assessments.append(a)
                result.alerts.append(self._alert(
                    severity="HIGH" if high else "WARN",
                    title="Control posture degraded",
                    subject="control_posture",
                    assessment=a.assessment.value,
                    recommended_action=a.recommended_action,
                    evidence=a.evidence,
                ))
            else:
                result.assessments.append(self._assessment(
                    subject="control_posture",
                    assessment=TruthAssessment.CONFIRMED_LIVE,
                    claimed_state="WITHIN_POLICY",
                    observed_state=f"posture={pct} high_findings={high}",
                    evidence=paths,
                    confidence=0.85,
                    recommended_action="NONE",
                    detail="Control posture within acceptable band for this sample.",
                ))

        # Scan snapshot strings for accidental secret material (read-only)
        blob = _flatten_strings(snapshot)
        hits = []
        for rx, label in _SECRET_PATTERNS:
            if rx.search(blob):
                hits.append(label)
        if hits:
            a = self._assessment(
                subject="secret_exposure_scan",
                assessment=TruthAssessment.BLOCKED,
                claimed_state="NO_SECRETS_IN_LEDGERS",
                observed_state=",".join(hits),
                evidence=paths + ["jspace_snapshot_scan"],
                confidence=0.8,
                recommended_action="QUARANTINE_REQUEST_SECRET_EXPOSURE",
                detail="Secret-shaped material detected in observed HELM surfaces.",
            )
            result.assessments.append(a)
            result.alerts.append(self._alert(
                severity="CRITICAL",
                title="Possible secret exposure in observed state",
                subject="secret_exposure_scan",
                assessment=a.assessment.value,
                recommended_action=a.recommended_action,
                evidence=a.evidence,
            ))
        else:
            result.assessments.append(self._assessment(
                subject="secret_exposure_scan",
                assessment=TruthAssessment.CONFIRMED_LIVE,
                claimed_state="NO_SECRETS_IN_LEDGERS",
                observed_state="CLEAN_SAMPLE",
                evidence=["jspace_snapshot_scan"],
                confidence=0.7,
                recommended_action="NONE",
                detail="No coarse secret patterns in sampled snapshot fields.",
            ))

        return result


def _flatten_strings(obj: Any, *, depth: int = 0) -> str:
    if depth > 6:
        return ""
    if isinstance(obj, str):
        return obj + "\n"
    if isinstance(obj, dict):
        return "".join(_flatten_strings(v, depth=depth + 1) for v in obj.values())
    if isinstance(obj, list):
        return "".join(_flatten_strings(v, depth=depth + 1) for v in obj[:100])
    return ""
