import pytest
import io
import zipfile
import hashlib
import os
from unittest.mock import patch, MagicMock
from backend.ledger_manager import get_handoff_status, create_handoff_packet
from backend.main import api_get_handoff_status, api_download_handoff_packet

def test_get_handoff_status_structure():
    status = get_handoff_status()
    
    assert "git" in status
    assert "branch" in status["git"]
    assert "commit_sha" in status["git"]
    assert "dirty" in status["git"]
    
    assert "gates" in status
    assert "preflight_score" in status["gates"]
    assert "preflight_pass" in status["gates"]
    assert "ledger_pass" in status["gates"]
    assert "model_health_pass" in status["gates"]
    assert "compliance_pass" in status["gates"]
    
    assert "manifest" in status
    assert len(status["manifest"]) > 0
    assert status["manifest"][0]["file"] == "swarm_ledger.db"

def test_create_handoff_packet_generation():
    zip_bytes = create_handoff_packet()
    assert isinstance(zip_bytes, bytes)
    assert len(zip_bytes) > 0
    
    zip_buffer = io.BytesIO(zip_bytes)
    with zipfile.ZipFile(zip_buffer, "r") as zip_file:
        file_list = zip_file.namelist()
        assert "ledger_blocks.json" in file_list
        assert "preflight_status.json" in file_list
        assert "model_health.json" in file_list
        assert "handoff_status.json" in file_list
        assert "manifest.sha256" in file_list
        
        # Verify manifest.sha256 matching hashes
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

def test_handoff_api_endpoints():
    status = api_get_handoff_status()
    assert "gates" in status
    assert "git" in status
    
    res = api_download_handoff_packet()
    assert res.media_type == "application/zip"
    assert "Content-Disposition" in res.headers
    assert "release_candidate_handoff_packet.zip" in res.headers["Content-Disposition"]
