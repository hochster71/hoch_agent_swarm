import pytest
import io
import zipfile
import hashlib
from unittest.mock import patch, MagicMock
from backend.ledger_manager import create_audit_review_bundle
from backend.main import api_download_evidence_bundle

def test_create_audit_review_bundle_generation():
    # Call the generator
    zip_bytes = create_audit_review_bundle()
    assert isinstance(zip_bytes, bytes)
    assert len(zip_bytes) > 0
    
    # Read the zip archive
    zip_buffer = io.BytesIO(zip_bytes)
    with zipfile.ZipFile(zip_buffer, "r") as zip_file:
        file_list = zip_file.namelist()
        assert "ledger_blocks.json" in file_list
        assert "chain_verification.json" in file_list
        assert "preflight_status.json" in file_list
        assert "model_health.json" in file_list
        assert "manifest.sha256" in file_list
        
        # Verify the manifest.sha256 checksums match the zip contents
        manifest_content = zip_file.read("manifest.sha256").decode("utf-8")
        manifest_lines = manifest_content.splitlines()
        
        for line in manifest_lines:
            if not line.strip():
                continue
            parts = line.split("  ")
            assert len(parts) == 2
            expected_sha = parts[0]
            filename = parts[1]
            
            # Read actual content from zip
            actual_content = zip_file.read(filename)
            actual_sha = hashlib.sha256(actual_content).hexdigest()
            assert actual_sha == expected_sha

def test_api_download_evidence_bundle_endpoint():
    res = api_download_evidence_bundle()
    assert res.media_type == "application/zip"
    assert "Content-Disposition" in res.headers
    assert "audit_evidence_review_bundle.zip" in res.headers["Content-Disposition"]
