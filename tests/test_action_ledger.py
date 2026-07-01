import pytest
import os
import json
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from backend.ledger_manager import log_operator_action, generate_evidence_pack, verify_ledger_chain
from backend.main import api_get_ledger_blocks, api_verify_ledger, api_get_evidence_pack

def test_log_operator_action_creates_valid_block():
    mock_preflight = {
        "go_no_go": "GO",
        "overall_score": 100,
        "checks": []
    }
    
    with patch("subprocess.run") as mock_run:
        # Mock git commands
        mock_git_rev = MagicMock()
        mock_git_rev.returncode = 0
        mock_git_rev.stdout = "fake_commit_sha_123\n"
        
        mock_git_status = MagicMock()
        mock_git_status.returncode = 0
        mock_git_status.stdout = ""
        
        mock_run.side_effect = [mock_git_rev, mock_git_status]
        
        block = log_operator_action(
            action_name="test_action",
            endpoint="/api/v1/test",
            preflight=mock_preflight,
            decision="GO",
            override_reason="",
            execution_output={"status": "ok"},
            artifact_refs=["/path/to/fake_ref.json"],
            recovery_command="echo 'recover'"
        )
        
        assert block["index"] > 0
        assert block["event"]["action"]["name"] == "test_action"
        assert block["event"]["action"]["endpoint"] == "/api/v1/test"
        assert block["event"]["decision"] == "GO"
        assert block["event"]["execution_context"]["git_state"]["commit_sha"] == "fake_commit_sha_123"
        assert block["event"]["execution_context"]["git_state"]["dirty"] is False
        assert block["event"]["execution_context"]["recovery_command"] == "echo 'recover'"
        assert block["event"]["execution_context"]["artifact_refs"] == ["/path/to/fake_ref.json"]

def test_verify_ledger_chain():
    res = verify_ledger_chain()
    assert res["is_valid"] is True
    assert res["block_count"] > 0

def test_generate_evidence_pack_returns_artifact_metadata(tmp_path):
    # Create a temp artifact file
    artifact_file = tmp_path / "artifact.json"
    artifact_data = {"key": "val"}
    artifact_file.write_text(json.dumps(artifact_data), encoding="utf-8")
    
    mock_preflight = {
        "go_no_go": "WARN",
        "overall_score": 80,
        "checks": []
    }
    
    # Write a test block to ledger
    block = log_operator_action(
        action_name="test_pack_generation",
        endpoint="/api/v1/test/pack",
        preflight=mock_preflight,
        decision="OVERRIDE",
        override_reason="Need to override",
        execution_output={"status": "ok"},
        artifact_refs=[str(artifact_file)],
        recovery_command="echo 'recover'"
    )
    
    pack = generate_evidence_pack(block["index"])
    
    assert pack["ledger_block"]["index"] == block["index"]
    assert pack["chain_verification"]["is_valid"] is True
    assert len(pack["artifacts_content"]) == 1
    assert pack["artifacts_content"][0]["path"] == str(artifact_file)
    assert pack["artifacts_content"][0]["is_text"] is True
    assert json.loads(pack["artifacts_content"][0]["content"]) == artifact_data

def test_api_endpoints_integration():
    blocks = api_get_ledger_blocks()
    assert len(blocks) > 0
    assert isinstance(blocks, list)
    
    verify_res = api_verify_ledger()
    assert verify_res["is_valid"] is True
    
    # Verify non-existent block raises 404
    with pytest.raises(HTTPException) as exc_info:
        api_get_evidence_pack(99999)
    assert exc_info.value.status_code == 404
