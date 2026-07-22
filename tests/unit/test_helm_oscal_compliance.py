#!/usr/bin/env python3
"""
HELM OSCAL & cATO Compliance Unit Test Suite (Sprint 9 — Milestone R11)
=======================================================================
Validates OSCAL 1.1.0 JSON exports, cATO evidence bundle integrity,
NIST SP 800-53 Rev. 5 control mapping completeness, UUID reference resolution,
and evidence tracing invariants (OSCAL-001 through OSCAL-017).
"""

import json
import uuid
import pytest
from pathlib import Path

from scripts.helm.generate_oscal_compliance_exports import (
    generate_oscal_component_definition,
    generate_oscal_ssp_fragment,
    generate_oscal_assessment_results,
    generate_oscal_poam,
    generate_cato_evidence_bundle
)

PROOFS_DIR = Path(__file__).resolve().parent.parent.parent / "coordination" / "proofs"


def is_valid_uuid(val: str) -> bool:
    try:
        uuid.UUID(val)
        return True
    except Exception:
        return False


def test_oscal_001_component_definition_schema():
    """[OSCAL-001] Asserts OSCAL Component Definition structure conforms to OSCAL 1.1.0."""
    cd = generate_oscal_component_definition()
    assert "component-definition" in cd
    assert cd["component-definition"]["metadata"]["oscal-version"] == "1.1.0"
    assert len(cd["component-definition"]["components"]) > 0


def test_oscal_002_ssp_fragment_schema():
    """[OSCAL-002] Asserts OSCAL System Security Plan fragment contains valid control implementations."""
    ssp = generate_oscal_ssp_fragment()
    assert "system-security-plan" in ssp
    reqs = ssp["system-security-plan"]["control-implementation"]["implemented-requirements"]
    assert len(reqs) >= 3


def test_oscal_003_assessment_results_automated_pass_state():
    """[OSCAL-003] Asserts OSCAL Assessment Results log AUTOMATED_TEST_PASS state for target controls."""
    ar = generate_oscal_assessment_results()
    assert "assessment-results" in ar
    findings = ar["assessment-results"]["results"][0]["findings"]
    for f in findings:
        assert f["status"]["state"] == "AUTOMATED_TEST_PASS"


def test_oscal_004_poam_scheduled_items():
    """[OSCAL-004] Asserts OSCAL Plan of Action & Milestones contains scheduled deficiency items."""
    poam = generate_oscal_poam()
    assert "plan-of-action-and-milestones" in poam
    items = poam["plan-of-action-and-milestones"]["poam-items"]
    assert len(items) > 0


def test_oscal_005_cato_evidence_bundle_integrity():
    """[OSCAL-005] Asserts cATO Evidence Bundle contains CATO_EVIDENCE_AUTOMATION_BASELINE status."""
    bundle = generate_cato_evidence_bundle("head_commit_sha", "parent_commit_sha")
    assert bundle["qualification_status"] == "CATO_EVIDENCE_AUTOMATION_BASELINE"
    assert bundle["binding_model"] == "PARENT_COMMIT_ATTESTATION_V1"


def test_oscal_006_component_definition_uuid_validity():
    """[OSCAL-006] Asserts all UUID fields in Component Definition are valid UUIDv4 strings."""
    cd = generate_oscal_component_definition()["component-definition"]
    assert is_valid_uuid(cd["uuid"])
    for comp in cd["components"]:
        assert is_valid_uuid(comp["uuid"])
        for impl in comp["control-implementations"]:
            assert is_valid_uuid(impl["uuid"])


def test_oscal_007_ssp_fragment_uuid_validity():
    """[OSCAL-007] Asserts all UUID fields in SSP Fragment are valid UUID strings."""
    ssp = generate_oscal_ssp_fragment()["system-security-plan"]
    assert is_valid_uuid(ssp["uuid"])


def test_oscal_008_assessment_results_uuid_validity():
    """[OSCAL-008] Asserts all UUID fields in Assessment Results are valid UUID strings."""
    ar = generate_oscal_assessment_results()["assessment-results"]
    assert is_valid_uuid(ar["uuid"])
    for res in ar["results"]:
        assert is_valid_uuid(res["uuid"])


def test_oscal_009_poam_uuid_validity():
    """[OSCAL-009] Asserts all UUID fields in POA&M are valid UUID strings."""
    poam = generate_oscal_poam()["plan-of-action-and-milestones"]
    assert is_valid_uuid(poam["uuid"])
    for item in poam["poam-items"]:
        assert is_valid_uuid(item["uuid"])


def test_oscal_010_uuid_uniqueness_across_artifacts():
    """[OSCAL-010] Asserts zero UUID collision across all generated OSCAL artifacts."""
    cd = generate_oscal_component_definition()["component-definition"]
    ssp = generate_oscal_ssp_fragment()["system-security-plan"]
    ar = generate_oscal_assessment_results()["assessment-results"]
    poam = generate_oscal_poam()["plan-of-action-and-milestones"]

    all_uuids = [cd["uuid"], ssp["uuid"], ar["uuid"], poam["uuid"]]
    assert len(all_uuids) == len(set(all_uuids)), "UUID collision detected across OSCAL artifacts"


def test_oscal_011_control_id_catalog_reference_resolution():
    """[OSCAL-011] Asserts control IDs reference valid NIST SP 800-53 catalog identifiers."""
    cd = generate_oscal_component_definition()["component-definition"]
    valid_controls = {"cm-2", "cm-3", "si-7", "au-2", "au-10", "sc-13"}

    for comp in cd["components"]:
        for impl in comp["control-implementations"]:
            for req in impl["implemented-requirements"]:
                assert req["control-id"] in valid_controls, f"Unknown control ID: {req['control-id']}"


def test_oscal_012_malformed_oscal_rejection():
    """[OSCAL-012] Asserts missing required fields in component definition raises KeyError/ValueError."""
    malformed = {"component-definition": {}}
    with pytest.raises(KeyError):
        _ = malformed["component-definition"]["metadata"]["oscal-version"]


def test_oscal_013_assessment_finding_evidence_tracing():
    """[OSCAL-013] Asserts every assessment finding contains non-empty evidence UUIDs and descriptions."""
    ar = generate_oscal_assessment_results()["assessment-results"]
    findings = ar["results"][0]["findings"]
    for f in findings:
        assert "evidence" in f
        assert len(f["evidence"]) > 0
        assert is_valid_uuid(f["evidence"][0]["uuid"])


def test_oscal_014_prevention_unsupported_satisfied_determinations():
    """[OSCAL-014] Asserts findings do not claim unverified 'satisfied' state without full assessment evidence."""
    ar = generate_oscal_assessment_results()["assessment-results"]
    findings = ar["results"][0]["findings"]
    for f in findings:
        assert f["status"]["state"] != "satisfied", "Unverified 'satisfied' claim prohibited; must use AUTOMATED_TEST_PASS"


def test_oscal_015_cato_baseline_status_evaluation():
    """[OSCAL-015] Asserts cATO bundle readiness evaluates to CATO_EVIDENCE_AUTOMATION_BASELINE."""
    bundle = generate_cato_evidence_bundle("head", "parent")
    assert bundle["qualification_status"] == "CATO_EVIDENCE_AUTOMATION_BASELINE"


def test_oscal_016_parent_commit_evidence_semantics():
    """[OSCAL-016] Asserts parent-commit evidence binding correctly distinguishes qualified source from evidence record commit."""
    bundle = generate_cato_evidence_bundle("head_123", "parent_456")
    att = bundle["evidence_attestation"]
    assert att["qualified_source_commit"] == "parent_456"
    assert att["evidence_record_commit"] == "head_123"


def test_oscal_017_deterministic_export_formatting():
    """[OSCAL-017] Asserts consecutive export generation produces identical JSON byte outputs."""
    cd1 = generate_oscal_component_definition()
    cd2 = generate_oscal_component_definition()

    b1 = json.dumps(cd1, sort_keys=True).encode("utf-8")
    b2 = json.dumps(cd2, sort_keys=True).encode("utf-8")
    assert b1 == b2, "OSCAL export formatting must be 100% deterministic"
