import os
from backend.model_router import model_registry

def test_model_registry_defaults():
    # Test that defaults are correctly loaded/returned
    assert model_registry.is_local_first() is True
    assert model_registry.are_paid_models_enabled() is False
    assert model_registry.get_default_provider() == "lmstudio"
    assert model_registry.get_default_model() == "google/gemma-4-12b-qat"

def test_model_providers_list():
    providers = model_registry.get_providers()
    assert "ollama" in providers
    assert "lmstudio" in providers
    assert "openai" in providers
    assert "anthropic" in providers

def test_enabled_providers():
    local_providers = model_registry.get_enabled_local_providers()
    paid_providers = model_registry.get_enabled_paid_providers()
    
    assert "ollama" in local_providers
    assert "lmstudio" in local_providers
    assert len(paid_providers) == 0  # paid providers are disabled by default
