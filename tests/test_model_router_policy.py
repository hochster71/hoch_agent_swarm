import pytest
from unittest.mock import patch
from backend.model_router import router, confidence

def test_confidence_evaluator():
    # Empty output returns low/0.0
    res = confidence.evaluate_confidence("")
    assert res["score"] == 0.0
    assert res["label"] == "low"
    assert "Empty" in res["reason"]
    
    res = confidence.evaluate_confidence("   ")
    assert res["score"] == 0.0
    
    # Valid output returns default high/0.85
    res = confidence.evaluate_confidence("This is a valid response from the local model server.")
    assert res["score"] == 0.85
    assert res["label"] == "high"

def test_router_fail_closed():
    # When local provider is unreachable and escalation is disabled, router fails closed
    with patch("backend.model_router.router.try_local_provider") as mock_local:
        mock_local.side_effect = router.RouterException("Local server offline")
        
        with pytest.raises(router.RouterException) as exc_info:
            router.route_and_run("Say hello")
            
        assert "No local model providers reachable" in str(exc_info.value)

def test_router_success_routing():
    # Test successful local model routing mock
    with patch("backend.model_router.router.try_local_provider") as mock_local:
        mock_local.return_value = "LOCAL ROUTER OK"
        
        res = router.route_and_run("Say hello")
        assert res["provider"] == "lmstudio"
        assert res["model"] == "google/gemma-4-12b-qat"
        assert res["output"] == "LOCAL ROUTER OK"
        assert res["paid_escalation_used"] is False
        assert res["audit_event_written"] is True
