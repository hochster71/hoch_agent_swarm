import os
import json
from typing import Dict, Any, List

class WarningBaselineManager:
    def __init__(self, baseline_path: str = None):
        if not baseline_path:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            baseline_path = os.path.join(project_root, "config/known_warning_baseline.json")
        self.baseline_path = baseline_path
        self.baseline = self._load_baseline()

    def _load_baseline(self) -> Dict[str, Any]:
        if os.path.exists(self.baseline_path):
            try:
                with open(self.baseline_path, "r") as f:
                    return json.load(f)
            except Exception:
                return {"warnings": []}
        return {"warnings": []}

    def evaluate_warning(self, warning_message: str, category: str = "Warning") -> Dict[str, Any]:
        msg = warning_message.lower().strip()
        
        # Clean prefix from msg
        clean_msg = msg
        for prefix in ["deprecationwarning:", "userwarning:", "runtimewarning:", "warning:", "starlettedeprecationwarning:"]:
            if clean_msg.startswith(prefix):
                clean_msg = clean_msg[len(prefix):].strip()

        # Check false positives
        if any(x in clean_msg for x in ["stub", "mock", "test_mock", "dummy"]):
            return {
                "status": "FALSE_POSITIVE",
                "owner": "QA Agent",
                "due_date": None,
                "is_new": False,
                "is_blocking": False
            }

        # Check matching baseline patterns
        for w in self.baseline.get("warnings", []):
            pat = w.get("message", "").lower().strip()
            if pat in clean_msg or clean_msg in pat:
                if w.get("accepted_risk", False):
                    return {
                        "status": "ACCEPTED_RISK",
                        "owner": w.get("owner", "Security Council"),
                        "due_date": w.get("due_date"),
                        "is_new": False,
                        "is_blocking": False
                    }
                return {
                    "status": "BASELINED_OWNED",
                    "owner": w.get("owner", "Refactor Agent"),
                    "due_date": w.get("due_date", "2026-07-29"),
                    "is_new": False,
                    "is_blocking": False
                }
        
        # If it's a known category of new warning that blocks
        if any(x in clean_msg for x in ["deprecation", "syntax", "runtime", "security"]):
            return {
                "status": "NEW_BLOCKING",
                "owner": "Refactor Agent",
                "due_date": None,
                "is_new": True,
                "is_blocking": True
            }

        return {
            "status": "UNKNOWN_BLOCKING",
            "owner": "Refactor Agent",
            "due_date": None,
            "is_new": True,
            "is_blocking": True
        }
