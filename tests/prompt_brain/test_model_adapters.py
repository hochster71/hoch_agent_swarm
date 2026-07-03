import os
import json
from pathlib import Path
from scripts.prompt_brain.model_adapters import (
    get_all_adapters,
    OpenAIAdapter,
    GeminiAdapter,
    ClaudeAdapter,
    SimulationFallbackAdapter
)

def test_get_all_adapters():
    adapters = get_all_adapters()
    assert len(adapters) == 6
    providers = [a.provider for a in adapters]
    assert "OpenAI" in providers
    assert "Anthropic" in providers
    assert "Google Gemini" in providers
    assert "HOCH Simulation" in providers

def test_simulation_fallback_adapter():
    adapter = SimulationFallbackAdapter()
    assert adapter.is_available is True
    
    res = adapter.execute(
        prompt_text="Audit cryptographic keys",
        input_payload={"test": 1},
        output_contract={}
    )
    assert res["status"] == "success"
    assert res["provider"] == "HOCH Simulation"
    assert "evidence" in res["output"]

def test_secret_masking():
    adapter = SimulationFallbackAdapter()
    masked = adapter.mask_secrets("My secret key is sk-1234567890abcdefghij.")
    assert "sk-" not in masked
    assert "[MASKED_KEY]" in masked

def test_health_checks():
    adapters = get_all_adapters()
    for a in adapters:
        res = a.health_check()
        assert isinstance(res, bool)
        assert a.last_health_check != ""

def test_openai_adapter_real_call_fails_on_invalid_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-mock-invalid-key-for-testing")
    adapter = OpenAIAdapter("gpt-4o-mini")
    adapter.health_check()
    assert adapter.is_available is True
    
    import pytest
    with pytest.raises(RuntimeError) as excinfo:
        adapter.execute("hello", {}, {})
    assert "OpenAI call failed" in str(excinfo.value)

def test_claude_adapter_real_call_fails_on_invalid_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-mock-invalid-key-for-testing")
    adapter = ClaudeAdapter("claude-3-5-sonnet-20241022")
    adapter.health_check()
    assert adapter.is_available is True
    
    import pytest
    with pytest.raises(RuntimeError) as excinfo:
        adapter.execute("hello", {}, {})
    assert "Claude call failed" in str(excinfo.value)
