from __future__ import annotations
import os
import tempfile
from pathlib import Path
from backend.audit_factory.control_registry import ControlRegistry
from backend.audit_factory.profile_loader import ProfileLoader
from backend.audit_factory.assessment_planner import AssessmentPlanner
from backend.audit_factory.evidence_validator import EvidenceValidator
from backend.audit_factory.provenance_validator import ProvenanceValidator
from backend.audit_factory.circular_evidence_detector import CircularEvidenceDetector
from backend.audit_factory.findings_engine import FindingsEngine
from backend.audit_factory.poam_engine import POAMEngine
from backend.audit_factory.certification_evaluator import CertificationEvaluator
from backend.audit_factory.conmon_engine import ConMonEngine
from backend.audit_factory.promotion_gate import evaluate_promotion
from backend.audit_factory.models import Control, Evidence, Finding, POAMItem, Milestone

def test_control_registry():
    registry = ControlRegistry()
    controls = registry.list_controls()
    assert len(controls) > 0
    assert any(c.control_id == "HAF-GOV-001" for c in controls)

def test_profile_loader():
    loader = ProfileLoader()
    active_common = loader.resolve_profile("helm_common")
    active_hasf = loader.resolve_profile("hasf_initial")
    assert "HAF-GOV-001" in active_common
    assert "HAF-SEC-001" in active_hasf
    # hasf_initial inherits helm_common
    assert "HAF-GOV-001" in active_hasf

def test_assessment_planner():
    registry = ControlRegistry()
    loader = ProfileLoader()
    planner = AssessmentPlanner(registry, loader)
    plan = planner.plan_assessment("helm_common")
    assert len(plan) > 0
    # verify sorting order is by level (L0 -> L1 -> etc.)
    levels = [c.level for c in plan]
    assert levels == sorted(levels)

def test_evidence_validator():
    validator = EvidenceValidator()
    with tempfile.NamedTemporaryFile("w", delete=False) as tf:
        tf.write("Sample test evidence bytes.")
        tf_name = tf.name

    try:
        import hashlib
        with open(tf_name, "rb") as f:
            valid_hash = hashlib.sha256(f.read()).hexdigest()

        ev = Evidence(
            evidence_id="EVD-HAF-20260719-1234",
            control_id="HAF-EVID-001",
            assessment_run_id="HAF-RUN-20260719-120000",
            source_type="FILE",
            source_path=tf_name,
            source_system="test",
            generated_at="2026-07-19T12:00:00Z",
            collected_at="2026-07-19T12:00:00Z",
            sha256=valid_hash,
            producer="test_runner",
            validator="test_validator",
            fresh_until="2026-07-26T12:00:00Z",
            status="UNVERIFIED"
        )
        assert validator.validate_evidence(ev) is True
        assert ev.status == "VALID"

        # Test hash mismatch
        ev.sha256 = "incorrect_sha_hash_value"
        assert validator.validate_evidence(ev) is False
        assert ev.status == "INVALID"
    finally:
        os.remove(tf_name)

def test_provenance_validator():
    validator = ProvenanceValidator()
    ev = Evidence(
        evidence_id="EVD-HAF-20260719-1234",
        control_id="HAF-EVID-001",
        assessment_run_id="HAF-RUN-20260719-120000",
        source_type="FILE",
        source_path="dummy",
        source_system="test",
        generated_at="2026-07-19T12:00:00Z",
        collected_at="2026-07-19T12:00:00Z",
        sha256="abc",
        producer="test_runner",
        validator="test_validator",
        fresh_until="2026-07-26T12:00:00Z",
        status="VALID"
    )
    assert validator.validate_provenance(ev) is True

def test_circular_evidence_detector():
    detector = CircularEvidenceDetector()
    detector.add_edge("ControlA", "EvidenceB")
    detector.add_edge("EvidenceB", "ValidatorC")
    detector.add_edge("ValidatorC", "ControlA")
    
    cycles = detector.detect_cycles()
    assert len(cycles) > 0
    assert any("ControlA" in c for c in cycles)

def test_findings_engine():
    engine = FindingsEngine()
    finding = engine.create_finding(
        control_id="HAF-GOV-001",
        run_id="HAF-RUN-20260719-120000",
        title="Unauthorized Gate Access Attempt",
        description="Bypass detected.",
        severity="HIGH"
    )
    assert finding.status == "OPEN"
    assert finding.control_id == "HAF-GOV-001"

def test_poam_engine():
    engine = POAMEngine()
    item = engine.create_poam_item(
        finding_ids=["FND-HAF-20260719-0001"],
        owner="HAF_ENGINEER",
        due_date="2026-07-26T12:00:00Z",
        severity="HIGH",
        remediation_plan="Fix the bypass logic."
    )
    assert item.status == "OPEN"
    
    # Try transitioning to CLOSED without retest success -> should reject
    assert engine.transition_status(item, "CLOSED", "HAF_ENGINEER", "Done", retest_success=False) is False
    assert item.status == "OPEN"

    # Try transitioning with retest success -> should pass
    assert engine.transition_status(item, "CLOSED", "HAF_ENGINEER", "Retest passed", retest_success=True) is True
    assert item.status == "CLOSED"

def test_certification_evaluator():
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
        status="FAIL"
    )
    decision = evaluator.evaluate_certification(
        scope="HELM_COMMON",
        level="L1",
        controls=[ctrl],
        evidences=[],
        open_critical_findings_count=0
    )
    assert decision.decision == "FAIL"

def test_conmon_engine():
    engine = ConMonEngine()
    signals = engine.evaluate_file_change("backend/council/founder_gate.py")
    assert len(signals) > 0
    assert any("HAF-GOV-001" in s.impacted_controls for s in signals)

def test_promotion_gate():
    # evaluate_promotion using temporary files
    with tempfile.NamedTemporaryFile("w", delete=False) as c_file, \
         tempfile.NamedTemporaryFile("w", delete=False) as f_file, \
         tempfile.NamedTemporaryFile("w", delete=False) as a_file:
        
        c_path = c_file.name
        f_path = f_file.name
        a_path = a_file.name

        c_file.write('{"decisions": [{"scope": "HELM_COMMON", "level": "L1", "decision": "PASS"}]}')
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
        assert decision.decision == "GO"
    finally:
        os.remove(c_path)
        os.remove(f_path)
        os.remove(a_path)
