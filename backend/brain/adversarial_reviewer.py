# adversarial_reviewer.py
import re
from pathlib import Path

class AdversarialReviewer:
    def __init__(self):
        # Compiled patterns for secret detection
        self.secret_patterns = [
            re.compile(r"sk-[a-zA-Z0-9\-]{32,}", re.IGNORECASE),  # OpenAI API keys
            re.compile(r"ghp_[a-zA-Z0-9]{36}", re.IGNORECASE),  # GitHub Personal Access Tokens
            re.compile(r"password\s*=\s*['\"][^'\"]+['\"]", re.IGNORECASE),
            re.compile(r"ssh-rsa\s+[a-zA-Z0-9+/=]+", re.IGNORECASE)  # SSH private/public keys
        ]

    def scan_proposal(self, action_description: str, file_path: str = None) -> dict:
        findings = []
        
        # 1. Audit write operation drift
        if file_path:
            p = Path(file_path).resolve()
            # Allowed directories: backend, frontend, config, docs/evidence, tests
            allowed = False
            root = Path(__file__).resolve().parent.parent.parent
            for folder in ["backend", "frontend", "config", "docs/evidence", "tests", "artifacts"]:
                if str(p).startswith(str(root / folder)):
                    allowed = True
                    break
            
            if not allowed:
                findings.append(f"Write operation outside allowed allowlist directories: {file_path}")
                
        # 2. Check for file mutations / deletions in action description
        if any(term in action_description.lower() for term in ["delete", "remove", "rename", "move"]):
            findings.append("Action includes potential destructive file modifications (rm/mv/rename).")

        # 3. Check for API secrets or tokens in description
        for pattern in self.secret_patterns:
            if pattern.search(action_description):
                findings.append("Potential secret key, API token, or SSH credential detected in description.")

        # 4. Check for public port binding
        if "0.0.0.0" in action_description or "publicly expose" in action_description.lower():
            findings.append("Proposal attempts to bind service to public interface (0.0.0.0).")

        status = "REJECTED" if len(findings) > 0 else "APPROVED"
        return {
            "status": status,
            "findings": findings,
            "decision_rule": "Enforced by Adversarial Reviewer v1.0.0",
            "requires_human_approval": status == "REJECTED"
        }
