from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel

class PromotionDecision(BaseModel):
    decision: str  # GO, HOLD, NO_GO
    blocking_controls: List[str]
    blocking_findings: List[str]
    expired_evidence: List[str]
    required_founder_gates: List[str]
    current_certification_level: str
    requested_target_level: str

def evaluate_promotion(
    scope: str,
    target_level: str,
    certification_registry_path: Path,
    findings_path: Path,
    approvals_path: Path,
) -> PromotionDecision:
    """Evaluates promotion criteria, verifying that no open findings or failed controls block the path."""
    blocking_controls = []
    blocking_findings = []
    expired_evidence = []
    required_founder_gates = []
    current_level = "L0"

    # 1. Read certification registry to check current active decisions
    if certification_registry_path.exists():
        try:
            cert_data = json.loads(certification_registry_path.read_text())
            # Find matching scope and level
            for dec in cert_data.get("decisions", []):
                if dec.get("scope") == scope:
                    current_level = dec.get("level", "L0")
                    if dec.get("decision") != "PASS":
                        reasons = dec.get("reasons", [])
                        if not reasons:
                            blocking_controls.append("HAF-PROM-001")
                        else:
                            for r in reasons:
                                blocking_controls.append(r.get("control_id") or "HAF-PROM-001")
        except Exception:
            blocking_controls.append("HAF-PROM-001")

    # 2. Read findings
    if findings_path.exists():
        try:
            findings_data = json.loads(findings_path.read_text())
            for fnd in findings_data.get("findings", []):
                if fnd.get("status") == "OPEN":
                    blocking_findings.append(fnd.get("finding_id"))
                    if fnd.get("severity") in ("CRITICAL", "HIGH"):
                        # High severity open findings trigger blocking controls
                        blocking_controls.append(fnd.get("control_id"))
        except Exception:
            blocking_findings.append("FND-READ-ERROR")

    # 3. Read approvals (e.g. founder gate checklists)
    if approvals_path.exists():
        try:
            approvals_data = json.loads(approvals_path.read_text())
            for app in approvals_data.get("gates", []):
                if app.get("status") != "approved":
                    required_founder_gates.append(app.get("gate_id"))
        except Exception:
            required_founder_gates.append("GATE-READ-ERROR")

    # logical decision rules
    if blocking_controls or blocking_findings:
        decision_str = "NO_GO"
    elif required_founder_gates:
        decision_str = "HOLD"
    else:
        decision_str = "GO"

    return PromotionDecision(
        decision=decision_str,
        blocking_controls=list(set(blocking_controls)),
        blocking_findings=list(set(blocking_findings)),
        expired_evidence=expired_evidence,
        required_founder_gates=required_founder_gates,
        current_certification_level=current_level,
        requested_target_level=target_level
    )
