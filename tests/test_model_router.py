import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from crewai import LLM
from hoch_agent_swarm.model_router import ModelRouter

@pytest.fixture
def mock_ollama_tags():
    # Mock tags response with mistral:7b and llama3.1:8b present
    tags_data = {
        "models": [
            {"name": "mistral:7b", "model": "mistral:7b"},
            {"name": "llama3.1:8b", "model": "llama3.1:8b"}
        ]
    }
    return tags_data

def test_get_available_models_success(mock_ollama_tags):
    # Reset cached models
    ModelRouter._available_models = None
    
    # Mock urllib.request.urlopen to return mock tags
    class FakeResponse:
        def read(self):
            return json.dumps(mock_ollama_tags).encode("utf-8")

    with patch("urllib.request.urlopen", return_value=FakeResponse()) as mock_urlopen:
        models = ModelRouter.get_available_models("http://localhost:11434")
        assert "mistral:7b" in models
        assert "llama3.1:8b" in models
        assert "qwen2.5-coder:14b" not in models
        mock_urlopen.assert_called_once_with("http://localhost:11434/api/tags", timeout=2.0)

def test_get_available_models_failure():
    # Reset cached models
    ModelRouter._available_models = None
    
    with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
        models = ModelRouter.get_available_models("http://localhost:11434")
        assert isinstance(models, set)
        assert len(models) == 0

def test_resolve_agent_llm_primary_available(tmp_path, monkeypatch):
    # Reset cached models
    ModelRouter._available_models = {"mistral:7b"}
    
    # Create temp config yaml
    config_content = """
routing:
  fast_classification:
    primary: "ollama/mistral:7b"
    fallback: "ollama/llama3.1:8b"
agents:
  cio: "fast_classification"
"""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "model_routing.yaml"
    config_file.write_text(config_content)
    
    # Patch Path to point to tmp_path
    with patch.object(Path, "exists", return_value=True), \
         patch("builtins.open", MagicMock(return_value=open(config_file))):
        llm = ModelRouter.resolve_agent_llm("cio")
        assert llm.model == "mistral:7b"

def test_resolve_agent_llm_fallback_when_primary_missing(tmp_path, monkeypatch):
    # Reset cached models: primary is missing, fallback is available
    ModelRouter._available_models = {"llama3.1:8b"}
    
    # Create temp config yaml
    config_content = """
routing:
  fast_classification:
    primary: "ollama/mistral:7b"
    fallback: "ollama/llama3.1:8b"
agents:
  cio: "fast_classification"
"""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "model_routing.yaml"
    config_file.write_text(config_content)
    
    # Patch Path to point to tmp_path
    with patch.object(Path, "exists", return_value=True), \
         patch("builtins.open", MagicMock(return_value=open(config_file))):
        llm = ModelRouter.resolve_agent_llm("cio")
        assert llm.model == "llama3.1:8b"

def test_resolve_agent_llm_env_default_when_all_missing(tmp_path, monkeypatch):
    # Reset cached models: all missing
    ModelRouter._available_models = set()
    monkeypatch.setenv("MODEL", "ollama/default-model:latest")
    
    # Create temp config yaml
    config_content = """
routing:
  fast_classification:
    primary: "ollama/mistral:7b"
    fallback: "ollama/llama3.1:8b"
agents:
  cio: "fast_classification"
"""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "model_routing.yaml"
    config_file.write_text(config_content)
    
    # Patch Path to point to tmp_path
    with patch.object(Path, "exists", return_value=True), \
         patch("builtins.open", MagicMock(return_value=open(config_file))):
        llm = ModelRouter.resolve_agent_llm("cio")
        assert llm.model == "default-model:latest"
