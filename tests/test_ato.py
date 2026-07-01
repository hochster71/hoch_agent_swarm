import pytest
import io
import zipfile
import hashlib
import json
from backend.ato_manager import get_ato_evidence_package, create_ato_evidence_zip
from backend.main import api_get_ato_evidence_package, api_download_ato_evidence_package

def test_get_ato_evidence_package_structure():
    pkg = get_ato_evidence_package()
    
    assert pkg["statement"] == "ATO-SUPPORTING EVIDENCE PACKAGE: READY FOR REVIEW"
    assert "The system has ATO-supporting evidence prepared for review" in pkg["status_notice"]
    assert "Actual ATO has not been granted" in pkg["status_notice"]
    assert "No authorization claim is being made" in pkg["status_notice"]
    
    assert "control_matrix" in pkg
    assert len(pkg["control_matrix"]) > 0
    assert pkg["control_matrix"][0]["control_id"] == "CM-2"
    
    assert "residual_risks" in pkg
    assert "poam" in pkg
    assert "ao_checklist" in pkg
    assert pkg["ao_checklist"][0]["check_id"] == "AO-CHECK-01"

def test_create_ato_evidence_zip():
    zip_bytes = create_ato_evidence_zip()
    assert isinstance(zip_bytes, bytes)
    assert len(zip_bytes) > 0
    
    zip_buffer = io.BytesIO(zip_bytes)
    with zipfile.ZipFile(zip_buffer, "r") as zip_file:
        file_list = zip_file.namelist()
        assert "rmf_evidence_package.json" in file_list
        assert "handoff/ledger_blocks.json" in file_list
        assert "manifest.sha256" in file_list
        
        # Verify all listed files exist in manifest.sha256 with matching checksums
        manifest_content = zip_file.read("manifest.sha256").decode("utf-8")
        lines = manifest_content.splitlines()
        for line in lines:
            if not line.strip():
                continue
            parts = line.split("  ")
            assert len(parts) == 2
            expected_sha = parts[0]
            filename = parts[1]
            
            actual_content = zip_file.read(filename)
            actual_sha = hashlib.sha256(actual_content).hexdigest()
            assert actual_sha == expected_sha

def test_ato_api_endpoints():
    pkg = api_get_ato_evidence_package()
    assert pkg["statement"] == "ATO-SUPPORTING EVIDENCE PACKAGE: READY FOR REVIEW"
    
    res = api_download_ato_evidence_package()
    assert res.media_type == "application/zip"
    assert "Content-Disposition" in res.headers
    assert "ato_evidence_package.zip" in res.headers["Content-Disposition"]
