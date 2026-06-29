import re
from typing import Dict, Any, List

class FinalVerifier:
    def __init__(self):
        self.forbidden_words = [
            r"\bfully complete\b",
            r"\b100%\b",
            r"\bproduction ready\b",
            r"\bno blockers\b",
            r"\bbest-in-class\b",
            r"\bfinal\b"
        ]

    def verify_final_report(self, report_text: str, active_gates_pass: bool, remaining_blockers: List[str]) -> Dict[str, Any]:
        # If active gates do NOT pass or we have remaining blockers, check for forbidden words
        detected = []
        if not active_gates_pass or len(remaining_blockers) > 0:
            for pattern in self.forbidden_words:
                if re.search(pattern, report_text.lower()):
                    match = re.search(pattern, report_text.lower()).group(0)
                    detected.append(match)

        if detected:
            return {
                "status": "BLOCKED",
                "reason": f"Forbidden absolute claims detected in report without gate validation: {', '.join(detected)}"
            }

        confidence_cap = 100.0
        if len(remaining_blockers) > 0:
            confidence_cap = 70.0

        return {
            "status": "VERIFIED" if active_gates_pass else "WARNING",
            "confidence_cap": confidence_cap,
            "detected_claims": detected
        }
