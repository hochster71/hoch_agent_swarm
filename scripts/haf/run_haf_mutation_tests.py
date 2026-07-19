#!/usr/bin/env python3
import os
import sys
import tempfile
import json
import yaml
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Resolve workspace root and inject into python path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, ROOT)

from backend.audit_factory.control_registry import ControlRegistry
from backend.audit_factory.evidence_validator import EvidenceValidator
from backend.audit_factory.circular_evidence_detector import CircularEvidenceDetector
from backend.audit_factory.service import HAFService
from backend.audit_factory.promotion_gate import evaluate_promotion
from backend.audit_factory.models import Control, Evidence

def log_test(name: str, status: str, detail: str = ""):
    status_color = "\033[92m[PASS]\033[0m" if status == "PASS" else "\033[91m[FAIL]\033[0m"
    print(f"  • {name:<45} {status_color} {detail}")

def run_mutation_tests():
    print("======================================================================")
    print("HOCH Audit Factory — HAF v0.1 Mutation Tests")
    print("Doctrine: no_fake_green · Fail Closed · Integrity Verification")
    print("======================================================================\n")

    overall_pass = True

    # -------------------------------------------------------------------------
    # Mutation 1: Remove required control fields
    # -------------------------------------------------------------------------
    try:
        # Load real catalog
        catalog_path = os.path.join(ROOT, "coordination/audit_factory/catalogs/control_catalog.yaml")
        with open(catalog_path, "r") as f:
            catalog_data = yaml.safe_load(f)
        
        # Mutate the first control by removing 'severity'
        mutated_control = dict(catalog_data["controls"][0])
        mutated_control.pop("severity", None)
        
        # Write to temporary catalog
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".yaml") as tmp:
            yaml.dump({"controls": [mutated_control]}, tmp)
            tmp_catalog_path = tmp.name

        try:
            # Loading this mutated catalog must trigger jsonschema.ValidationError
            ControlRegistry(catalog_path=tmp_catalog_path)
            log_test("MUTATION-001: Missing Control Fields", "FAIL", "Failed to detect missing 'severity' field")
            overall_pass = False
        except Exception as e:
            log_test("MUTATION-001: Missing Control Fields", "PASS", f"Successfully intercepted missing field: {type(e).__name__}")
        finally:
            os.remove(tmp_catalog_path)
    except Exception as e:
        print(f"Error in MUTATION-001: {e}")
        overall_pass = False

    # -------------------------------------------------------------------------
    # Mutation 2: Alter evidence hashes
    # -------------------------------------------------------------------------
    try:
        validator = EvidenceValidator()
        with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
            tmp.write("Authentic audit trail file content.")
            tmp_file_path = tmp.name

        try:
            # Correct hash
            with open(tmp_file_path, "rb") as f:
                correct_hash = hashlib.sha256(f.read()).hexdigest()

            ev = Evidence(
                evidence_id="EVD-HAF-20260719-1111",
                control_id="HAF-EVID-001",
                assessment_run_id="HAF-RUN-20260719-120000",
                source_type="FILE",
                source_path=tmp_file_path,
                source_system="test",
                generated_at="2026-07-19T12:00:00Z",
                collected_at="2026-07-19T12:00:00Z",
                sha256="incorrect_tampered_hash_value_123456",
                producer="test",
                validator="test",
                fresh_until="2026-07-26T12:00:00Z",
                status="UNVERIFIED"
            )
            # Validation must return False and set status to INVALID
            is_valid = validator.validate_evidence(ev)
            if not is_valid and ev.status == "INVALID":
                log_test("MUTATION-002: Altered Evidence Hashes", "PASS", "Intercepted altered hash and marked INVALID")
            else:
                log_test("MUTATION-002: Altered Evidence Hashes", "FAIL", f"Failed to detect mismatch (valid={is_valid}, status={ev.status})")
                overall_pass = False
        finally:
            os.remove(tmp_file_path)
    except Exception as e:
        print(f"Error in MUTATION-002: {e}")
        overall_pass = False

    # -------------------------------------------------------------------------
    # Mutation 3: Invalidate JSON schemas
    # -------------------------------------------------------------------------
    try:
        # Create an evidence with invalid field types
        with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
            tmp.write("content")
            tmp_file_path = tmp.name

        try:
            ev = Evidence(
                evidence_id="EVD-HAF-20260719-2222",
                control_id="HAF-EVID-001",
                assessment_run_id="HAF-RUN-20260719-120000",
                source_type="FILE",
                source_path=tmp_file_path,
                source_system="test",
                generated_at="2026-07-19T12:00:00Z",
                collected_at="2026-07-19T12:00:00Z",
                sha256="abc",
                producer="test",
                validator="test",
                fresh_until="2026-07-26T12:00:00Z",
                status="INVALID" # invalid type status
            )
            validator = EvidenceValidator()
            # Force status to something not in the schema enum
            ev_dict = ev.model_dump()
            ev_dict["status"] = "NOT_A_VALID_STATUS_ENUM_VALUE"
            
            import jsonschema
            try:
                jsonschema.validate(instance=ev_dict, schema=validator.schema)
                log_test("MUTATION-003: Invalidate JSON Schemas", "FAIL", "Allowed invalid status enum value")
                overall_pass = False
            except jsonschema.ValidationError as e:
                log_test("MUTATION-003: Invalidate JSON Schemas", "PASS", f"Detected schema validation error: {e.message[:40]}...")
        finally:
            os.remove(tmp_file_path)
    except Exception as e:
        print(f"Error in MUTATION-003: {e}")
        overall_pass = False

    # -------------------------------------------------------------------------
    # Mutation 4: Introduce circular evidence
    # -------------------------------------------------------------------------
    try:
        detector = CircularEvidenceDetector()
        detector.add_edge("HAF-IND-001", "EVD-HAF-20260719-9999")
        detector.add_edge("EVD-HAF-20260719-9999", "HAF-IND-001") # Circular dependency
        
        cycles = detector.detect_cycles()
        if cycles:
            log_test("MUTATION-004: Circular Evidence Chain", "PASS", f"Detected cycle: {' -> '.join(cycles[0])}")
        else:
            log_test("MUTATION-004: Circular Evidence Chain", "FAIL", "Failed to detect circular validation dependency")
            overall_pass = False
    except Exception as e:
        print(f"Error in MUTATION-004: {e}")
        overall_pass = False

    # -------------------------------------------------------------------------
    # Mutation 5: Create stale evidence
    # -------------------------------------------------------------------------
    try:
        validator = EvidenceValidator()
        with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
            tmp.write("content")
            tmp_file_path = tmp.name

        try:
            with open(tmp_file_path, "rb") as f:
                h = hashlib.sha256(f.read()).hexdigest()

            # fresh_until set 1 day in the past
            stale_time = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

            ev = Evidence(
                evidence_id="EVD-HAF-20260719-3333",
                control_id="HAF-EVID-001",
                assessment_run_id="HAF-RUN-20260719-120000",
                source_type="FILE",
                source_path=tmp_file_path,
                source_system="test",
                generated_at="2026-07-19T12:00:00Z",
                collected_at="2026-07-19T12:00:00Z",
                sha256=h,
                producer="test",
                validator="test",
                fresh_until=stale_time,
                status="UNVERIFIED"
            )
            is_valid = validator.validate_evidence(ev)
            if not is_valid and ev.status == "STALE":
                log_test("MUTATION-005: Create Stale Evidence", "PASS", "Intercepted stale evidence and marked STALE")
            else:
                log_test("MUTATION-005: Create Stale Evidence", "FAIL", f"Failed to mark STALE (valid={is_valid}, status={ev.status})")
                overall_pass = False
        finally:
            os.remove(tmp_file_path)
    except Exception as e:
        print(f"Error in MUTATION-005: {e}")
        overall_pass = False

    # -------------------------------------------------------------------------
    # Mutation 6: Create duplicate queue IDs
    # -------------------------------------------------------------------------
    try:
        # Create a temp escalation queue with duplicate decision_ids
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".jsonl") as tmp:
            tmp.write(json.dumps({"decision_id": "DEC-TEST-99", "queued_at": 100}) + "\n")
            tmp.write(json.dumps({"decision_id": "DEC-TEST-99", "queued_at": 200}) + "\n")
            tmp_queue_path = tmp.name

        try:
            service = HAFService(workspace_root=ROOT)
            ctrl = service.control_registry.get_control("HAF-QUEUE-001")
            
            # Temporarily point escalation queue check path to our mutated temp file
            import unittest.mock as mock
            with mock.patch("os.path.join", side_effect=lambda *args: tmp_queue_path if "escalation_queue.jsonl" in args[-1] else os.path.abspath(os.path.join(*args))):
                status, msg = service._evaluate_control_status(ctrl)
            
            if status == "FAIL" and "duplicate" in msg.lower():
                log_test("MUTATION-006: Duplicate Queue IDs", "PASS", f"Detected duplicate queue IDs: {msg}")
            else:
                log_test("MUTATION-006: Duplicate Queue IDs", "FAIL", f"Failed to detect duplicate (status={status}, msg={msg})")
                overall_pass = False
        finally:
            os.remove(tmp_queue_path)
    except Exception as e:
        print(f"Error in MUTATION-006: {e}")
        overall_pass = False

    # -------------------------------------------------------------------------
    # Mutation 7: Promotion Gate Fail-Closed (Mandatory FAIL Blocker)
    # -------------------------------------------------------------------------
    try:
        with tempfile.NamedTemporaryFile("w", delete=False) as c_file, \
             tempfile.NamedTemporaryFile("w", delete=False) as f_file, \
             tempfile.NamedTemporaryFile("w", delete=False) as a_file:
            
            c_path = c_file.name
            f_path = f_file.name
            a_path = a_file.name

            # Write a failed target decision
            c_file.write('{"decisions": [{"scope": "HELM_COMMON", "level": "L1", "decision": "FAIL"}]}')
            f_file.write('{"findings": []}')
            a_file.write('{"gates": []}')

        try:
            decision = evaluate_promotion(
                scope="HELM_COMMON",
                target_level="L1",
                certification_registry_path=Path(c_path),
                findings_path=Path(f_path),
                approvals_path=Path(a_path)
            )
            if decision.decision == "NO_GO" and "HAF-PROM-001" in decision.blocking_controls:
                log_test("MUTATION-007: Promotion Gate Fail-Closed", "PASS", "Blocked promotion on target certification FAIL")
            else:
                log_test("MUTATION-007: Promotion Gate Fail-Closed", "FAIL", f"Failed to block (decision={decision.decision})")
                overall_pass = False
        finally:
            os.remove(c_path)
            os.remove(f_path)
            os.remove(a_path)
    except Exception as e:
        print(f"Error in MUTATION-007: {e}")
        overall_pass = False

    print("\n----------------------------------------------------------------------")
    if overall_pass:
        print("\033[92mALL MUTATION TESTS DETECTED SUCCESSFULLY [PASS]\033[0m")
        sys.exit(0)
    else:
        print("\033[91mSOME MUTATION TESTS FAILED [FAIL]\033[0m")
        sys.exit(1)

if __name__ == "__main__":
    run_mutation_tests()
