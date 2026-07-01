import re
import os
import yaml

class DataClassifier:
    def __init__(self, root_dir=None):
        from backend.runtime_paths import project_root
        if root_dir is None:
            root_dir = str(project_root())
        self.root_dir = root_dir
        self.policy_path = os.path.join(root_dir, "config/rbac_policy.yaml")

    def classify_request(self, requester: str, text: str) -> dict:
        text_lower = text.lower()
        
        # Identity validation
        if requester in ["unknown", "guest"]:
            return {
                "classification": "restricted",
                "allowed": False,
                "reason": "Unauthenticated or guest operator requests are blocked by default."
            }

        # Check for sensitive key terms
        sensitive_terms = ["credentials", "secrets", "password", ".env", "api key", "private key", "ssh"]
        if any(term in text_lower for term in sensitive_terms):
            if requester != "michael":
                return {
                    "classification": "sensitive",
                    "allowed": False,
                    "reason": "Sensitive operations involving credentials/keys are restricted to Michael Hoch."
                }
            return {
                "classification": "sensitive",
                "allowed": True,
                "reason": "Allowed for administrative operator (Michael Hoch)."
            }

        # Check for work internal key terms
        work_terms = ["bmc3", "saic", "sda", "work", "dark wolf", "defense", "military", "rmf", "ato"]
        if any(term in text_lower for term in work_terms):
            if requester != "michael":
                return {
                    "classification": "work internal",
                    "allowed": False,
                    "reason": "Work Internal artifacts/data access is blocked for family/non-admin users."
                }
            return {
                "classification": "work internal",
                "allowed": True,
                "reason": "Allowed for admin operator."
            }

        # Check for family terms
        family_terms = ["family", "alison", "caroline", "claire", "school", "pool", "chores", "routines"]
        if any(term in text_lower for term in family_terms):
            return {
                "classification": "family",
                "allowed": True,
                "reason": "Safe household data scope."
            }

        # Default to public
        return {
            "classification": "public",
            "allowed": True,
            "reason": "Public data scope. No sensitive or work references found."
        }
