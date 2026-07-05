from typing import Dict, Any, List
from backend.final_verifier.completion_contract import CompletionContract
from backend.final_verifier.contradiction_checker import ContradictionChecker
from backend.final_verifier.readiness_cap_engine import ReadinessCapEngine
from backend.final_verifier.blocker_reporter import BlockerReporter
from backend.final_verifier.evidence_validator import EvidenceValidator
from backend.final_verifier.ui_truth_validator import UiTruthValidator
from backend.final_verifier.defect_zero_validator import DefectZeroValidator
from backend.final_verifier.runtime_truth_contract import RuntimeTruthVerdictGuard

class FinalVerdict:
    def __init__(self):
        self.contract = CompletionContract()
        self.contradiction = ContradictionChecker()
        self.cap_engine = ReadinessCapEngine()
        self.blocker = BlockerReporter()
        self.evidence = EvidenceValidator()
        self.ui_truth = UiTruthValidator()
        self.defect_zero = DefectZeroValidator()
        self.runtime_truth_guard = RuntimeTruthVerdictGuard()

    def get_final_verdict(self) -> Dict[str, Any]:
        contract_res = self.contract.verify_text("") # will check files/policies
        cap_res = self.cap_engine.calculate_caps()
        contradiction_res = self.contradiction.check_contradictions(readiness_override=cap_res["score"])
        blocker_res = self.blocker.get_active_blockers()

        # Merge contradiction violations into blockers list
        if not contradiction_res["is_valid"]:
            if "blockers" not in blocker_res:
                blocker_res["blockers"] = []
            for v in contradiction_res["violations"]:
                b_type = "RUNTIME_CONTRADICTION"
                if "GO and NO-GO contradiction" in v:
                    b_type = "GO_NO_GO_CONTRADICTION"
                blocker_res["blockers"].append({
                    "type": b_type,
                    "description": v
                })
            blocker_res["blocker_count"] = len(blocker_res["blockers"])

        evidence_res = self.evidence.validate_recent_evidence()
        ui_truth_res = self.ui_truth.validate_ui_truth()
        defect_zero_res = self.defect_zero.validate_defects()

        provisional_valid = (
            contradiction_res["is_valid"] and
            evidence_res["is_valid"] and
            ui_truth_res["is_valid"] and
            defect_zero_res["is_valid"] and
            blocker_res.get("blocker_count", 0) == 0
        )

        # Runtime Truth Contract guard: a provisional VERIFIED (green) verdict is
        # only contract-legal if readiness is not not-ready-capped. Fails open, so
        # it can only tighten a would-be-green verdict, never loosen a blocked one.
        provisional_status = "VERIFIED" if provisional_valid else "BLOCKED"
        guard_res = self.runtime_truth_guard.validate_verdict(
            provisional_status, cap_res["score"]
        )

        all_valid = provisional_valid and guard_res["is_valid"]
        status = "VERIFIED" if all_valid else "BLOCKED"

        return {
            "status": status,
            "readiness_score": cap_res["score"],
            "readiness_caps": cap_res["caps"],
            "runtime_truth_contract": {
                "is_valid": guard_res["is_valid"],
                "reason": guard_res["reason"],
                "violations": guard_res["violations"]
            },
            "contradiction_checker": {
                "is_valid": contradiction_res["is_valid"],
                "violations": contradiction_res["violations"]
            },
            "evidence_validator": {
                "is_valid": evidence_res["is_valid"],
                "violations": evidence_res.get("violations", [])
            },
            "ui_truth_validator": {
                "is_valid": ui_truth_res["is_valid"],
                "violations": ui_truth_res["violations"]
            },
            "defect_zero_validator": {
                "is_valid": defect_zero_res["is_valid"],
                "violations": defect_zero_res["violations"]
            },
            "blocker_reporter": {
                "blocker_count": blocker_res.get("blocker_count", 0),
                "blockers": blocker_res.get("blockers", [])
            }
        }
