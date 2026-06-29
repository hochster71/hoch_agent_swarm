import yaml
import os
from typing import Dict, Any, List

class CompletionContract:
    def __init__(self, policy_path: str = "config/final_verifier_policy.yaml"):
        self.policy_path = policy_path
        self.policy = self._load_policy()

    def _load_policy(self) -> Dict[str, Any]:
        if os.path.exists(self.policy_path):
            with open(self.policy_path, "r") as f:
                return yaml.safe_load(f) or {}
        return {}

    def get_forbidden_words(self) -> List[str]:
        return self.policy.get("final_verifier_policy", {}).get("forbidden_words", [])

    def verify_text(self, text: str) -> Dict[str, Any]:
        """
        Scans text for unqualified absolute claims.
        Claims are allowed if they are scoped (e.g. "100% of active tests passed").
        """
        forbidden = self.get_forbidden_words()
        violations = []
        for word in forbidden:
            if word in text.lower():
                # Check if it is scoped
                # A simple heuristic: if the sentence contains "of" or "passed" or "closed" or "fresh",
                # it's considered scoped.
                sentences = text.split(".")
                for s in sentences:
                    if word in s.lower():
                        is_scoped = any(x in s.lower() for x in ["of", "passed", "closed", "fresh", "assigned", "limit", "bound"])
                        if not is_scoped:
                            violations.append(f"Unqualified claim found: '{word}' in sentence: '{s.strip()}'")

        return {
            "is_valid": len(violations) == 0,
            "violations": violations
        }
