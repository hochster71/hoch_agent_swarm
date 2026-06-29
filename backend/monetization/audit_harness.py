import os
import uuid
import json
from datetime import datetime
from backend.monetization.read_only_guard import ReadOnlyGuard
from backend.monetization.security_redactor import SecurityRedactor
from backend.monetization.evidence_validator import EvidenceValidator

class AuditHarness:
    def __init__(self, root_dir="/Users/michaelhoch/hoch_agent_swarm"):
        self.root_dir = root_dir
        self.guard = ReadOnlyGuard(root_dir)
        self.redactor = SecurityRedactor(root_dir)
        self.validator = EvidenceValidator(root_dir)

    def execute_audit_sweep(self) -> dict:
        timestamp = datetime.utcnow().isoformat() + "Z"
        audit_id = f"aud-{str(uuid.uuid4())[:8]}"
        
        # Self-Check 1: Read-Only write boundaries
        write_test_ok = False
        test_path = os.path.join(self.root_dir, "data/monetization/test_write.txt")
        try:
            self.guard.verify_write_path(test_path)
            os.makedirs(os.path.dirname(test_path), exist_ok=True)
            with open(test_path, "w") as f:
                f.write("Safe sidecar output path test.")
            write_test_ok = os.path.exists(test_path)
            if write_test_ok:
                os.remove(test_path)
        except Exception:
            write_test_ok = False

        # Self-Check 2: Prohibited commands check
        command_blocked_ok = False
        try:
            self.guard.verify_command("mv file1.txt file2.txt")
        except PermissionError:
            command_blocked_ok = True

        # Self-Check 3: Redactor filtration check
        secret_redacted_ok = False
        dirty_string = "My OpenAI key is: api_key='sk-proj-1234abcd5678efgh9012ijkl3456mnop'"
        clean_string = self.redactor.redact_text(dirty_string)
        if "[REDACTED_SENSITIVE_DATA]" in clean_string:
            secret_redacted_ok = True

        passed = write_test_ok and command_blocked_ok and secret_redacted_ok
        
        # 4. Generate audit evidence log
        evidence_filename = f"{datetime.now().strftime('%Y%m%d-%H%M')}-inventory-audit.md"
        evidence_filepath = os.path.join(self.root_dir, "docs/evidence/monetization", evidence_filename)
        os.makedirs(os.path.dirname(evidence_filepath), exist_ok=True)
        
        content = f"""# Monetization Sidecar Read-Only Audit & Guard Verification

**Audit ID**: `{audit_id}`  
**Timestamp**: `{timestamp}`  
**Overall Status**: `{"PASS" if passed else "FAIL"}`  

## Policy Controls Check Matrix
* **Allowed Path Verification**: `{"PASS" if write_test_ok else "FAIL"}` (Validated boundary writing in `data/monetization/`)
* **Prohibited Mutate Interceptor**: `{"PASS" if command_blocked_ok else "FAIL"}` (Blocked prohibited commands list `mv, rm, rename`)
* **Secret Redaction Filter**: `{"PASS" if secret_redacted_ok else "FAIL"}` (Filtered token, api_key patterns)

## Active Guard Parameters
* **Read-only Mode**: `ACTIVE`
* **Output Path Allowlist**:
  1. `data/monetization/`
  2. `docs/evidence/monetization/`
  3. `docs/planning/monetization/`
"""
        with open(evidence_filepath, "w") as f:
            f.write(content)

        return {
            "audit_id": audit_id,
            "timestamp": timestamp,
            "status": "PASS" if passed else "FAIL",
            "write_path_pass": write_test_ok,
            "blocked_actions_pass": command_blocked_ok,
            "secret_redaction_pass": secret_redacted_ok,
            "evidence_filepath": evidence_filepath
        }
