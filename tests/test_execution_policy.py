import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from backend.execution_policy import POLICY_ENGINE

@pytest.fixture(autouse=True)
def clean_ci_env(monkeypatch):
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("TEST_MODE", raising=False)

def test_execution_policy_go_by_default():
    # Setup mock preflight status returning GO
    mock_preflight = {
        "go_no_go": "GO",
        "overall_score": 100,
        "checks": [
            {"id": "port_check", "name": "Required Ports", "status": "PASS", "message": "All ports open"}
        ]
    }
    with patch("backend.preflight_gate.GATE.run_preflight", return_value=mock_preflight):
        result = POLICY_ENGINE.enforce("test_action")
        assert result is True

def test_execution_policy_no_go_blocks_by_default():
    # Setup mock preflight status returning NO-GO
    mock_preflight = {
        "go_no_go": "NO-GO",
        "overall_score": 75,
        "checks": [
            {"id": "disk_space", "name": "Free Disk Space", "status": "FAIL", "message": "Disk space critically low"},
            {"id": "port_check", "name": "Required Ports", "status": "PASS", "message": "All ports open"}
        ]
    }
    with patch("backend.preflight_gate.GATE.run_preflight", return_value=mock_preflight):
        with pytest.raises(HTTPException) as exc_info:
            POLICY_ENGINE.enforce("test_action", override=False)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"] == "PREFLIGHT_BLOCKED"
        assert exc_info.value.detail["go_no_go"] == "NO-GO"
        assert len(exc_info.value.detail["checks"]) == 2

def test_execution_policy_no_go_allows_override_with_audit():
    # Setup mock preflight status returning NO-GO
    mock_preflight = {
        "go_no_go": "NO-GO",
        "overall_score": 50,
        "checks": [
            {"id": "disk_space", "name": "Free Disk Space", "status": "FAIL", "message": "Disk space critically low"},
            {"id": "git_dirty", "name": "Clean Git Status", "status": "WARN", "message": "Workspace has dirty files"}
        ]
    }
    
    with patch("backend.preflight_gate.GATE.run_preflight", return_value=mock_preflight), \
         patch("backend.model_router.audit_log.log_routing_event") as mock_log:
        
        mock_log.return_value = True
        
        # Enforce with override=True
        result = POLICY_ENGINE.enforce("test_action", override=True)
        
        # Verify it passed and logged the audit trail event
        assert result is True
        mock_log.assert_called_once()
        
        args, kwargs = mock_log.call_args
        assert args[0] == "preflight_override"
        payload = args[1]
        assert payload["action"] == "test_action"
        assert payload["preflight_score"] == 50
        assert "disk_space" in payload["failed_checks"]
        assert "git_dirty" in payload["warning_checks"]
