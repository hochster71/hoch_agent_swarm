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
        # Check matching baseline patterns
        for w in self.baseline.get("warnings", []):
            pat = w.get("message", "").lower()
            msg = warning_message.lower()
            if pat in msg or msg in pat:
                return {
                    "status": "LEGACY_DEBT",
                    "owner": w.get("owner", "Refactor Agent"),
                    "due_date": w.get("due_date", "2026-07-29"),
                    "is_new": False
                }
        
        return {
            "status": "NEW_WARNING_FAIL",
            "owner": "Refactor Agent",
            "due_date": None,
            "is_new": True
        }
