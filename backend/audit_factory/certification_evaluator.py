from __future__ import annotations
import json
import os
from datetime import datetime, timezone, timedelta
import jsonschema
from backend.audit_factory.models import CertificationDecision, Control, Reason, Evidence

class CertificationEvaluator:
    def __init__(self, schema_path: str = None):
        self.schema_path = schema_path or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../coordination/audit_factory/schemas/certification_decision.schema.json")
        )
        self.schema = None
        if os.path.exists(self.schema_path):
            with open(self.schema_path, "r") as f:
                self.schema = json.load(f)

    def evaluate_certification(
        self,
        scope: str,
        level: str,
        controls: list[Control],
        evidences: list[Evidence],
        open_critical_findings_count: int,
        negative_tests_present: bool = True,
        lower_level_expired: bool = False,
        limitations_present: bool = False
    ) -> CertificationDecision:
        decision_id = f"DEC-HAF-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{os.urandom(2).hex()}"
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        expires_str = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")

        reasons = []
        result = "HOLD"

        # Check mandatory control outcomes
        failed_mandatory = [c for c in controls if c.mandatory and c.status == "FAIL"]
        unassessed_mandatory = [c for c in controls if c.mandatory and c.status in ("NOT_ASSESSED", "IN_PROGRESS", "EXPIRED")]

        # Check evidence outcomes
        invalid_evidence = [e for e in evidences if e.status in ("INVALID", "STALE", "UNVERIFIED")]

        if failed_mandatory:
            result = "FAIL"
            for c in failed_mandatory:
                reasons.append(Reason(control_id=c.control_id, reason="Mandatory control failed"))
        elif open_critical_findings_count > 0:
            result = "HOLD"
            reasons.append(Reason(control_id="HAF-PROM-001", reason=f"Found {open_critical_findings_count} open critical finding(s)"))
        elif unassessed_mandatory:
            result = "HOLD"
            for c in unassessed_mandatory:
                reasons.append(Reason(control_id=c.control_id, reason=f"Mandatory control status is {c.status}"))
        elif invalid_evidence:
            result = "HOLD"
            for e in invalid_evidence:
                reasons.append(Reason(control_id=e.control_id, reason=f"Evidence {e.evidence_id} is {e.status}"))
        elif not negative_tests_present:
            result = "HOLD"
            reasons.append(Reason(control_id="HAF-PROM-001", reason="Required negative tests are absent"))
        elif lower_level_expired:
            result = "HOLD"
            reasons.append(Reason(control_id="HAF-PROM-001", reason="Lower-level certification has expired"))
        elif all(c.status == "PASS" for c in controls if c.mandatory):
            if limitations_present:
                result = "PASS_WITH_LIMITATIONS"
                reasons.append(Reason(control_id="HAF-PROM-001", reason="Pass achieved with documented engineering limitations"))
            else:
                result = "PASS"
        else:
            result = "HOLD"
            reasons.append(Reason(control_id="HAF-PROM-001", reason="Unmet control conditions"))

        decision_obj = CertificationDecision(
            decision_id=decision_id,
            scope=scope,
            level=level,
            decision=result,
            reasons=reasons,
            assessed_at=now_str,
            expires_at=expires_str,
            evaluator="certification_evaluator",
            operating_posture="AUTHORIZED" if result in ("PASS", "PASS_WITH_LIMITATIONS") else "RESTRICTED"
        )

        if self.schema:
            jsonschema.validate(instance=decision_obj.model_dump(), schema=self.schema)

        return decision_obj
