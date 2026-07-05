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
    with patch("backend.model_router.router.try_local_provider") as mock_local, \
         patch("backend.model_router.model_registry.get_default_provider", return_value="lmstudio"), \
         patch("backend.model_router.model_registry.get_default_model", return_value="google/gemma-4-12b-qat"):
        mock_local.return_value = "LOCAL ROUTER OK"
        
        res = router.route_and_run("Say hello")
        assert res["provider"] == "lmstudio"
        assert res["model"] == "google/gemma-4-12b-qat"
        assert res["output"] == "LOCAL ROUTER OK"
        assert res["paid_escalation_used"] is False
        assert res["audit_event_written"] is True

def test_router_fallback_failover():
    # If primary local provider (lmstudio) fails, check that it fails over to the fallback local provider (ollama).
    def mock_try(provider, model, prompt):
        if provider == "lmstudio":
            raise router.RouterException("LM Studio offline")
        elif provider == "ollama":
            return "FALLBACK LOCAL OLLAMA OK"
        raise router.RouterException("Unknown provider")

    with patch("backend.model_router.router.try_local_provider", side_effect=mock_try), \
         patch("backend.model_router.model_registry.get_default_provider", return_value="lmstudio"), \
         patch("backend.model_router.model_registry.get_default_model", return_value="google/gemma-4-12b-qat"), \
         patch("backend.model_router.model_registry.get_providers", return_value={
             "lmstudio": {"enabled": True, "type": "local", "models": ["google/gemma-4-12b-qat"]},
             "ollama": {"enabled": True, "type": "local", "models": ["qwen2.5-coder:7b"]}
         }):
        res = router.route_and_run("Say hello")
        assert res["provider"] == "ollama"
        assert res["model"] == "qwen2.5-coder:7b"
        assert res["output"] == "FALLBACK LOCAL OLLAMA OK"
        assert res["paid_escalation_used"] is False

def test_router_data_egress_block():
    # If the provider is a paid/cloud provider (like openai) and the prompt contains secrets/credentials
    # It must block the request and raise a RouterException
    with patch("backend.model_router.model_registry.get_default_provider", return_value="openai"):
        with pytest.raises(router.RouterException) as exc_info:
            router.route_and_run("My secret password is 12345")
        assert "Data egress block" in str(exc_info.value)

def test_router_data_egress_block_escalation():
    # If local models fail and we try to escalate a sensitive prompt, the escalation block must catch it
    def mock_try(provider, model, prompt):
        raise router.RouterException("Local server offline")

    with patch("backend.model_router.router.try_local_provider", side_effect=mock_try), \
         patch("backend.model_router.model_registry.are_paid_models_enabled", return_value=True), \
         patch("backend.model_router.escalation_policy.check_escalation_policy", return_value={"allowed": True}):
        
        with pytest.raises(router.RouterException) as exc_info:
            router.route_and_run("Please store this customer personal_info: John Doe")
        assert "Data egress block" in str(exc_info.value)

