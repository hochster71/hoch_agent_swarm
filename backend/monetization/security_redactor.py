import re
import os
import yaml

class SecurityRedactor:
    def __init__(self, root_dir=None):
        from backend.runtime_paths import project_root
        if root_dir is None:
            root_dir = str(project_root())
        self.root_dir = root_dir
        self.policy_path = os.path.join(root_dir, "config/monetization_audit_policy.yaml")
        self.redact_patterns = [
            r"(?i)api[_-]?key\s*[:=]\s*['\"][^'\"]+['\"]",
            r"(?i)secret\s*[:=]\s*['\"][^'\"]+['\"]",
            r"(?i)token\s*[:=]\s*['\"][^'\"]+['\"]",
            r"(?i)password\s*[:=]\s*['\"][^'\"]+['\"]",
            r"(?i)private_key\s*[:=]\s*['\"][^'\"]+['\"]",
            # SECURITY FIX 2026-07-20. Was r"sk-[a-zA-Z0-9]{32,}" — no hyphen or
            # underscore in the character class, so it could NOT match modern OpenAI
            # keys (sk-proj-…, sk-svcacct-…): the hyphen after the prefix terminates
            # the match. Effect: if config/monetization_audit_policy.yaml is absent or
            # unreadable, load_policy() leaves these defaults in place and redaction
            # silently degrades to a NO-OP for the most common live key format.
            # A redactor that fails open is worse than none — callers believe output
            # is safe. Fallback must be at least as strong as the policy pattern.
            r"sk-[a-zA-Z0-9_-]{20,}",
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
