import pytest
import io
import zipfile
import json
from backend.cybergov_manager import (
    get_cybergov_scorecard,
    get_cybergov_data,
    generate_cybergov_reports_bundle
)
from backend.main import (
    api_get_cybergov_data,
    api_get_cybergov_scorecard,
    api_get_cybergov_reports_bundle
)
from backend.ato_manager import create_ato_evidence_zip

def test_cybergov_scorecard():
    scorecard = get_cybergov_scorecard()
    # Check required disclaimers/targets
    assert scorecard["framework_coverage_target"] == "100% framework coverage mapping target"
    assert scorecard["control_traceability_target"] == "100% control-to-evidence traceability target"
    assert scorecard["reporting_coverage_target"] == "100% reporting coverage target"
    
    # Ensure correct safety language
    notice = scorecard["compliance"]["notice"]
    assert "The system has ATO-supporting evidence prepared for review" in notice
    assert "Actual ATO has not been granted" in notice
    assert "No authorization claim is being made" in notice
    
    # Block forbidden claims
    assert "ATO granted" not in notice
    assert "compliant by default" not in notice

def test_cybergov_data_tables():
    data = get_cybergov_data()
    # Verify tables
    assert "controls" in data
    assert "control_families" in data
    assert "evidence" in data
    assert "assessments" in data
    assert "findings" in data
    assert "poams" in data
    assert "risks" in data
    assert "conmon_events" in data
    assert "framework_sources" in data
    assert "crosswalks" in data
    
    # Verify control parameters
    controls = data["controls"]
    assert len(controls) > 0
    c1 = controls[0]
    required_keys = [
        "control_id", "family", "title", "baseline_applicability",
        "implementation_status", "assessment_status", "evidence_refs",
        "owner", "frequency", "last_assessed", "next_due", "risk_rating",
        "poam_link", "framework_source", "source_citation"
    ]
    for key in required_keys:
        assert key in c1

def test_reports_bundle():
    bundle = generate_cybergov_reports_bundle()
    # Check all 12 reports exist
    keys = [
        "1_nist_800_53_rev5_control_implementation_matrix",
        "2_nist_800_53a_assessment_results_matrix",
        "3_nist_sp_800_137_conmon_report",
        "4_rmf_lifecycle_status_report",
        "5_poam_export",
        "6_risk_register_export",
        "7_evidence_traceability_matrix",
        "8_cisa_kev_cpg_coverage_report",
        "9_dod_zero_trust_crosswalk",
        "10_ao_review_package",
        "11_executive_cybersecurity_scorecard",
        "12_machine_readable_json_evidence_bundle"
    ]
    for key in keys:
        assert key in bundle

def test_api_endpoints():
    data = api_get_cybergov_data()
    assert "controls" in data
    
    scorecard = api_get_cybergov_scorecard()
    assert "framework_coverage_target" in scorecard
    
    bundle = api_get_cybergov_reports_bundle()
    assert len(bundle) == 12

def test_ato_zip_inclusion():
    zip_bytes = create_ato_evidence_zip()
    zip_buffer = io.BytesIO(zip_bytes)
    
    with zipfile.ZipFile(zip_buffer, "r") as zf:
        namelist = zf.namelist()
        # Verify RMF primary metadata
        assert "rmf_evidence_package.json" in namelist
        
        # Verify CyberGov reports subdirectory inclusion
        assert "cybergov/1_nist_800_53_rev5_control_implementation_matrix.json" in namelist
        assert "cybergov/5_poam_export.json" in namelist
        assert "cybergov/9_dod_zero_trust_crosswalk.json" in namelist
        assert "cybergov/12_machine_readable_json_evidence_bundle.json" in namelist
        
        # Verify manifest list tracks cybergov
        assert "manifest.sha256" in namelist
        manifest = zf.read("manifest.sha256").decode("utf-8")
        assert "cybergov/1_nist_800_53_rev5_control_implementation_matrix.json" in manifest
