import os
import glob
from typing import Dict, Any, List

class EvidenceValidator:
    def __init__(self, evidence_dir: str = "docs/evidence"):
        self.evidence_dir = evidence_dir

    def validate_recent_evidence(self) -> Dict[str, Any]:
        """
        Validates that at least one evidence file has been generated and contains no unqualified claims.
        """
        files = glob.glob(os.path.join(self.evidence_dir, "**/*.md"), recursive=True)
        if not files:
            return {
                "is_valid": False,
                "reason": "No evidence files found in docs/evidence/",
                "validated_files": []
            }

        # Sort by modification time, get the most recent one
        files.sort(key=os.path.getmtime, reverse=True)
        latest_file = files[0]

        try:
            with open(latest_file, "r") as f:
                content = f.read()
        except Exception as e:
            return {
                "is_valid": False,
                "reason": f"Failed to read latest evidence file {latest_file}: {str(e)}",
                "validated_files": []
            }

        # Scan for forbidden words
        from backend.final_verifier.completion_contract import CompletionContract
        contract = CompletionContract()
        res = contract.verify_text(content)

        return {
            "is_valid": res["is_valid"],
            "reason": "Checked latest evidence file" if res["is_valid"] else f"Violations in {latest_file}: {', '.join(res['violations'])}",
            "validated_files": [latest_file],
            "violations": res.get("violations", [])
        }
