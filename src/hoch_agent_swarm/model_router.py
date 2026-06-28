import os
import urllib.request
import urllib.error
import json
import yaml
from pathlib import Path
from crewai import LLM

class ModelRouter:
    _available_models = None

    @classmethod
    def get_available_models(cls, api_base: str) -> set[str]:
        if cls._available_models is not None:
            return cls._available_models

        cls._available_models = set()
        url = f"{api_base.rstrip('/')}/api/tags"
        try:
            req = urllib.request.urlopen(url, timeout=2.0)
            data = json.loads(req.read().decode("utf-8"))
            for model_info in data.get("models", []):
                name = model_info.get("name", "")
                if name:
                    cls._available_models.add(name)
                model_field = model_info.get("model", "")
                if model_field:
                    cls._available_models.add(model_field)
        except Exception:
            # Under offline/test conditions, we gracefully ignore network failures
            pass
        return cls._available_models

    @classmethod
    def resolve_agent_llm(cls, agent_name: str) -> LLM:
        # Load environment defaults
        default_model = os.getenv("MODEL", "ollama/llama3.1:8b")
        api_base = os.getenv("API_BASE", "http://localhost:11434")

        base_dir = Path(__file__).resolve().parent
        config_path = base_dir / "config" / "model_routing.yaml"
        
        if not config_path.exists():
            return LLM(model=default_model, base_url=api_base)

        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f) or {}
        except Exception:
            return LLM(model=default_model, base_url=api_base)

        agent_class = config.get("agents", {}).get(agent_name)
        if not agent_class:
            return LLM(model=default_model, base_url=api_base)

        routing_rule = config.get("routing", {}).get(agent_class)
        if not routing_rule:
            return LLM(model=default_model, base_url=api_base)

        primary = routing_rule.get("primary")
        fallback = routing_rule.get("fallback")

        # Query live model availability in Ollama
        available = cls.get_available_models(api_base)

        # Helper to strip provider prefix for checking
        def strip_prefix(m: str) -> str:
            if m.startswith("ollama/"):
                return m[len("ollama/"):]
            return m

        # Check primary
        if primary:
            norm_primary = strip_prefix(primary)
            if norm_primary in available or primary in available:
                return LLM(model=primary, base_url=api_base)

        # Check fallback
        if fallback:
            norm_fallback = strip_prefix(fallback)
            if norm_fallback in available or fallback in available:
                return LLM(model=fallback, base_url=api_base)

        # Final default fallback
        return LLM(model=default_model, base_url=api_base)
