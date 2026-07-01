import os
import yaml
from typing import Dict, Any

class DefectClassifier:
    def __init__(self, policy_path: str = None):
        if not policy_path:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            policy_path = os.path.join(project_root, "config/zero_defect_policy.yaml")
        self.policy_path = policy_path
        self.policy = self._load_policy()

    def _load_policy(self) -> Dict[str, Any]:
        if os.path.exists(self.policy_path):
            with open(self.policy_path, "r") as f:
                return yaml.safe_load(f) or {}
        return {}

    def classify(self, defect_desc: str, domain: str, file_path: str = None) -> Dict[str, Any]:
        desc_lower = defect_desc.lower()
        
        # Default severity mapping
        severity = "MEDIUM"
        safe_auto_fix = True
        owner_agent = "Refactor Agent"

        if "syntaxerror" in desc_lower or "critical" in desc_lower or "crash" in desc_lower:
            severity = "CRITICAL"
            safe_auto_fix = False
            owner_agent = "Architect Agent"
        elif "failed" in desc_lower or "error" in desc_lower or "unreachable" in desc_lower:
            severity = "HIGH"
            safe_auto_fix = False
            owner_agent = "Pytest Agent"
        elif "warning" in desc_lower or "deprecation" in desc_lower:
            severity = "MEDIUM"
            safe_auto_fix = True
            owner_agent = "Refactor Agent"
        elif "formatting" in desc_lower or "style" in desc_lower or "whitespace" in desc_lower:
            severity = "LOW"
            safe_auto_fix = True
            owner_agent = "Lint Agent"

        # Override based on domain
        if domain == "security":
            owner_agent = "Security Reviewer"
            safe_auto_fix = False
        elif domain == "frontend":
            owner_agent = "Playwright Agent"

        return {
            "severity": severity,
            "domain": domain,
            "owner_agent": owner_agent,
            "safe_auto_fix": safe_auto_fix
        }
