import pytest
from pathlib import Path
import os
import shutil
from backend.monetization.read_only_guard import ReadOnlyGuard
from backend.monetization.security_redactor import SecurityRedactor
from backend.monetization.evidence_validator import EvidenceValidator
from backend.monetization.audit_harness import AuditHarness

# FIXTURE DEFECT FIXED 2026-07-20: was hardcoded f"{ROOT_DIR}".
# That path exists on exactly one machine. Elsewhere the policy YAML silently fails to
# load (masking the weak-default redaction bug) and mkdir under /Users raises
# PermissionError. Resolve from the test file instead.
ROOT_DIR = str(Path(__file__).resolve().parents[2])

def test_read_only_guard_allowed_paths():
    guard = ReadOnlyGuard(ROOT_DIR)
    
    # Allowed writes
    guard.verify_write_path(f"{ROOT_DIR}/data/monetization/test.json")
    guard.verify_write_path(f"{ROOT_DIR}/docs/evidence/monetization/report.md")
    guard.verify_write_path(f"{ROOT_DIR}/docs/planning/monetization/package.md")

    # Blocked writes (outside allowlist)
    with pytest.raises(PermissionError):
        guard.verify_write_path(f"{ROOT_DIR}/backend/main.py")
        
    with pytest.raises(PermissionError):
        guard.verify_write_path("/Users/michaelhoch/Documents/secrets.txt")

def test_read_only_guard_command_blocking():
    guard = ReadOnlyGuard(ROOT_DIR)
    
    # Normal reads
    guard.verify_command("cat /Users/michaelhoch/hoch_agent_swarm/README.md")
    
    # Prohibited mutations
    with pytest.raises(PermissionError):
        guard.verify_command("mv file1 file2")
        
    with pytest.raises(PermissionError):
        guard.verify_command("rm -rf /")

def test_security_redactor_credential_filter():
    redactor = SecurityRedactor(ROOT_DIR)
    
    clean = redactor.redact_text("Here is sk-proj-1234abcd5678efgh9012ijkl3456mnop and key='secret-token'")
    assert "[REDACTED_SENSITIVE_DATA]" in clean
    assert "sk-proj-" not in clean

def test_evidence_validator():
    validator = EvidenceValidator(ROOT_DIR)
    
    # Non-existent evidence file
    res = validator.validate_project_evidence("p-1", "Cyber-brief", ["data/nonexistent.txt"])
    assert not res["valid"]
    assert "Path does not exist" in res["error"]
    
    # Valid non-empty file
    test_file = os.path.join(ROOT_DIR, "data/monetization/test_evidence.txt")
    os.makedirs(os.path.dirname(test_file), exist_ok=True)
    with open(test_file, "w") as f:
        f.write("Some valid project content.")
        
    try:
        res2 = validator.validate_project_evidence("p-1", "Cyber-brief", ["data/monetization/test_evidence.txt"])
        assert res2["valid"]
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)

def test_audit_harness_sweep():
    harness = AuditHarness(ROOT_DIR)
    res = harness.execute_audit_sweep()
    assert res["status"] == "PASS"
    assert res["write_path_pass"]
    assert res["blocked_actions_pass"]
    assert res["secret_redaction_pass"]
    assert os.path.exists(res["evidence_filepath"])
