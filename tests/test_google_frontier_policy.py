import os
import pytest
from unittest.mock import patch, MagicMock
from backend.model_router.google_frontier import call_google_frontier, GoogleFrontierException

@pytest.fixture
def mock_configs():
    with patch("backend.model_router.google_frontier.load_escalation_config") as mock_esc, \
         patch("backend.model_router.google_frontier.load_approvals") as mock_app:
        
        # Default mock escalation config (disabled by default)
        mock_esc.return_value = {
            "escalation": {
                "enabled": False,
                "allowed_reasons": ["general", "high_complexity"],
                "high_risk_keywords": ["destructive", "secrets"]
            },
            "google_frontier": {
                "enabled": False,
                "max_single_call_usd": 1.0,
                "allowed_models": ["gemini-3.1-flash-lite"],
                "blocked_payload_classes": ["secrets", "credentials"]
            }
        }
        
        # Default mock approvals list
        mock_app.return_value = {
            "approvals": [
                {
                    "approval_id": "esc-test-ok",
                    "status": "APPROVED",
                    "expires_at": "2030-01-01T00:00:00Z"
                },
                {
                    "approval_id": "esc-test-expired",
                    "status": "APPROVED",
                    "expires_at": "2020-01-01T00:00:00Z"
                },
                {
                    "approval_id": "esc-test-pending",
                    "status": "PENDING",
                    "expires_at": "2030-01-01T00:00:00Z"
                }
            ]
        }
        yield mock_esc, mock_app

def test_google_frontier_disabled_by_default(mock_configs):
    # Should raise error when escalation is disabled globally
    with pytest.raises(GoogleFrontierException, match="disabled globally"):
        call_google_frontier("gemini-3.1-flash-lite", "test prompt", "general", "esc-test-ok")

def test_google_frontier_missing_api_key(mock_configs):
    mock_esc, _ = mock_configs
    mock_esc.return_value["escalation"]["enabled"] = True
    mock_esc.return_value["google_frontier"]["enabled"] = True
    
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(GoogleFrontierException, match="Missing GOOGLE_API_KEY"):
            call_google_frontier("gemini-3.1-flash-lite", "test prompt", "general", "esc-test-ok")

def test_google_frontier_unallowed_reason(mock_configs):
    mock_esc, _ = mock_configs
    mock_esc.return_value["escalation"]["enabled"] = True
    mock_esc.return_value["google_frontier"]["enabled"] = True
    
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
        with pytest.raises(GoogleFrontierException, match="not in allowed reasons"):
            call_google_frontier("gemini-3.1-flash-lite", "test prompt", "unallowed_reason", "esc-test-ok")

def test_google_frontier_expired_approval(mock_configs):
    mock_esc, _ = mock_configs
    mock_esc.return_value["escalation"]["enabled"] = True
    mock_esc.return_value["google_frontier"]["enabled"] = True
    
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
        with pytest.raises(GoogleFrontierException, match="expired"):
            call_google_frontier("gemini-3.1-flash-lite", "test prompt", "general", "esc-test-expired")

def test_google_frontier_pending_approval(mock_configs):
    mock_esc, _ = mock_configs
    mock_esc.return_value["escalation"]["enabled"] = True
    mock_esc.return_value["google_frontier"]["enabled"] = True
    
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
        with pytest.raises(GoogleFrontierException, match="not APPROVED"):
            call_google_frontier("gemini-3.1-flash-lite", "test prompt", "general", "esc-test-pending")

def test_google_frontier_payload_safety_block(mock_configs):
    mock_esc, _ = mock_configs
    mock_esc.return_value["escalation"]["enabled"] = True
    mock_esc.return_value["google_frontier"]["enabled"] = True
    
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
        # Keyword "destructive" is in high_risk_keywords
        with pytest.raises(GoogleFrontierException, match="destructive"):
            call_google_frontier("gemini-3.1-flash-lite", "run destructive script", "general", "esc-test-ok")
