from __future__ import annotations
import os
import tempfile
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from backend.audit_factory.evidence_validator import EvidenceValidator
from backend.audit_factory.circular_evidence_detector import CircularEvidenceDetector
from backend.audit_factory.certification_evaluator import CertificationEvaluator
from backend.audit_factory.promotion_gate import evaluate_promotion
from backend.audit_factory.models import Control, Evidence, Finding

def test_evidence_tamper_detection():
    validator = EvidenceValidator()
    with tempfile.NamedTemporaryFile("w", delete=False) as tf:
        tf.write("Original content")
        tf_name = tf.name

    try:
        # Generate initial valid hash
        with open(tf_name, "rb") as f:
            valid_hash = hashlib.sha256(f.read()).hexdigest()

        ev = Evidence(
            evidence_id="EVD-HAF-20260719-0001",
            control_id="HAF-EVID-001",
            assessment_run_id="HAF-RUN-20260719-120000",
            source_type="FILE",
            source_path=tf_name,
            source_system="test",
            generated_at="2026-07-19T12:00:00Z",
            collected_at="2026-07-19T12:00:00Z",
            sha256=valid_hash,
            producer="test",
            validator="test",
            fresh_until="2026-07-26T12:00:00Z",
            status="UNVERIFIED"
        )
        assert validator.validate_evidence(ev) is True
        assert ev.status == "VALID"

        # Tamper the file content
        with open(tf_name, "w") as f:
            f.write("Tampered content")

        # Validation must fail closed with INVALID status due to hash mismatch
        assert validator.validate_evidence(ev) is False
        assert ev.status == "INVALID"
        assert "hash mismatch" in ev.metadata.get("validation_error", "").lower()
    finally:
        os.remove(tf_name)


def test_stale_evidence():
    validator = EvidenceValidator()
    with tempfile.NamedTemporaryFile("w", delete=False) as tf:
        tf.write("Current content")
        tf_name = tf.name

    try:
        with open(tf_name, "rb") as f:
            valid_hash = hashlib.sha256(f.read()).hexdigest()

        # Set fresh_until in the past
        past_time = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

        ev = Evidence(
            evidence_id="EVD-HAF-20260719-0002",
            control_id="HAF-EVID-001",
            assessment_run_id="HAF-RUN-20260719-120000",
            source_type="FILE",
            source_path=tf_name,
            source_system="test",
            generated_at="2026-07-19T12:00:00Z",
            collected_at="2026-07-19T12:00:00Z",
            sha256=valid_hash,
            producer="test",
            validator="test",
            fresh_until=past_time,
            status="UNVERIFIED"
        )
        # Validation must fail due to expired freshness
        assert validator.validate_evidence(ev) is False
        assert ev.status == "STALE"
    finally:
        os.remove(tf_name)


def test_missing_evidence_resolves_to_hold():
    evaluator = CertificationEvaluator()
    ctrl = Control(
        control_id="HAF-GOV-001",
        version="1.0.0",
        level="L2",
        domain="Governance",
        family="Gov",
        title="Founder Gate",
        requirement="None",
        severity="CRITICAL",
        mandatory=True,
        assessment_procedure_ids=[],
        freshness_period_hours=168,
        failure_effect="FAIL",
        status="PASS"
    )
    # Evidence is UNVERIFIED (missing/invalid)
    ev = Evidence(
        evidence_id="EVD-HAF-20260719-0003",
        control_id="HAF-GOV-001",
        assessment_run_id="HAF-RUN-20260719-120000",
        source_type="FILE",
        source_path="non_existent_file.json",
        source_system="test",
        generated_at="2026-07-19T12:00:00Z",
        collected_at="2026-07-19T12:00:00Z",
        sha256="abc",
        producer="test",
        validator="test",
        fresh_until="2026-07-26T12:00:00Z",
        status="UNVERIFIED"
    )

    decision = evaluator.evaluate_certification(
        scope="HELM_COMMON",
        level="L1",
        controls=[ctrl],
        evidences=[ev],
        open_critical_findings_count=0
    )
    # Must be HOLD due to invalid/missing evidence
    assert decision.decision == "HOLD"
    assert any("evidence" in r.reason.lower() for r in decision.reasons)


def test_fail_closed_mandatory_policy():
    evaluator = CertificationEvaluator()
    ctrl = Control(
        control_id="HAF-GOV-001",
        version="1.0.0",
        level="L2",
        domain="Governance",
        family="Gov",
        title="Founder Gate",
        requirement="None",
        severity="CRITICAL",
        mandatory=True,
        assessment_procedure_ids=[],
        freshness_period_hours=168,
        failure_effect="FAIL",
        status="FAIL"  # Mandatory control fails
    )

    decision = evaluator.evaluate_certification(
        scope="HELM_COMMON",
        level="L1",
        controls=[ctrl],
        evidences=[],
        open_critical_findings_count=0
    )
    # Must be FAIL overall
    assert decision.decision == "FAIL"


def test_circular_dependency_rejection():
    detector = CircularEvidenceDetector()
    detector.add_edge("HAF-IND-001", "EVD-HAF-001")
    detector.add_edge("EVD-HAF-001", "HAF-IND-001") # Circular citation
    
    cycles = detector.detect_cycles()
    assert len(cycles) > 0
    assert "HAF-IND-001" in cycles[0]


def test_promotion_gate_mandatory_fail():
    with tempfile.NamedTemporaryFile("w", delete=False) as c_file, \
         tempfile.NamedTemporaryFile("w", delete=False) as f_file, \
         tempfile.NamedTemporaryFile("w", delete=False) as a_file:
        
        c_path = c_file.name
        f_path = f_file.name
        a_path = a_file.name

        # Write a decision with FAIL status
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
        # Promotion must produce NO_GO due to failed target certification
        assert decision.decision == "NO_GO"
    finally:
        os.remove(c_path)
        os.remove(f_path)
        os.remove(a_path)


def test_mutation_suite_execution():
    from scripts.haf.run_haf_mutation_tests import run_mutation_tests
    import unittest.mock as mock
    with mock.patch("sys.exit") as mock_exit:
        run_mutation_tests()
        if mock_exit.called:
            assert mock_exit.call_args[0][0] == 0
