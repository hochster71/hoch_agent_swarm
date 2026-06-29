import re
import os
import yaml

class SecurityRedactor:
    def __init__(self, root_dir="/Users/michaelhoch/hoch_agent_swarm"):
        self.root_dir = root_dir
        self.policy_path = os.path.join(root_dir, "config/monetization_audit_policy.yaml")
        self.redact_patterns = [
            r"(?i)api[_-]?key\s*[:=]\s*['\"][^'\"]+['\"]",
            r"(?i)secret\s*[:=]\s*['\"][^'\"]+['\"]",
            r"(?i)token\s*[:=]\s*['\"][^'\"]+['\"]",
            r"(?i)password\s*[:=]\s*['\"][^'\"]+['\"]",
            r"(?i)private_key\s*[:=]\s*['\"][^'\"]+['\"]",
            r"sk-[a-zA-Z0-9]{32,}"
        ]
        self.load_policy()

    def load_policy(self):
        if os.path.exists(self.policy_path):
            with open(self.policy_path, "r") as f:
                data = yaml.safe_load(f) or {}
            policy = data.get("monetization_audit_policy", {})
            raw_patterns = policy.get("redact_patterns", [])
            if raw_patterns:
                # Compile standard keyword matches if specified
                self.redact_patterns = []
                for p in raw_patterns:
                    if p.startswith("sk-"):
                        self.redact_patterns.append(r"sk-[a-zA-Z0-9_-]{20,}")
                    else:
                        self.redact_patterns.append(rf"(?i){p}\s*[:=]\s*['\"][^'\"]+['\"]")

    def redact_text(self, text: str) -> str:
        redacted = text
        for pattern in self.redact_patterns:
            redacted = re.sub(pattern, "[REDACTED_SENSITIVE_DATA]", redacted)
        return redacted
