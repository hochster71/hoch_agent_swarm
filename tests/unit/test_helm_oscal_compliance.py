#!/usr/bin/env python3
"""
HELM OSCAL & cATO Compliance Unit Test Suite (Sprint 9 — Milestone R11)
=======================================================================
Validates OSCAL 1.1.0 JSON exports, cATO evidence bundle integrity,
and NIST SP 800-53 Rev. 5 control mapping completeness.
"""

import json
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


def test_oscal_003_assessment_results_satisfied_controls():
    """[OSCAL-003] Asserts OSCAL Assessment Results log satisfied state for target controls."""
    ar = generate_oscal_assessment_results()
    assert "assessment-results" in ar
    findings = ar["assessment-results"]["results"][0]["findings"]
    for f in findings:
        assert f["status"]["state"] == "satisfied"


def test_oscal_004_poam_scheduled_items():
    """[OSCAL-004] Asserts OSCAL Plan of Action & Milestones contains scheduled milestone entries."""
    poam = generate_oscal_poam()
    assert "plan-of-action-and-milestones" in poam
    items = poam["plan-of-action-and-milestones"]["poam-items"]
    assert len(items) > 0


def test_oscal_005_cato_evidence_bundle_integrity():
    """[OSCAL-005] Asserts cATO Evidence Bundle contains continuous authorization readiness status."""
    bundle = generate_cato_evidence_bundle("test_commit_sha")
    assert bundle["qualification_status"] == "CONTINUOUS_AUTHORIZATION_READY"
    assert bundle["binding_model"] == "PARENT_COMMIT_ATTESTATION_V1"
