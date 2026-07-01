import os
import yaml
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "models.yaml"

def load_config():
    if not CONFIG_PATH.exists():
        # Safe defaults if config does not exist
        return {
            "local_first": True,
            "paid_models_enabled": False,
            "default_provider": "lmstudio",
            "default_model": "google/gemma-4-12b-qat",
            "providers": {}
        }
    
    try:
        with open(CONFIG_PATH, "r") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Error loading models config: {e}")
        return {
            "local_first": True,
            "paid_models_enabled": False,
            "default_provider": "lmstudio",
            "default_model": "google/gemma-4-12b-qat",
            "providers": {}
        }

def get_default_provider() -> str:
    cfg = load_config()
    return cfg.get("default_provider", "lmstudio")

def get_default_model() -> str:
    cfg = load_config()
    return cfg.get("default_model", "google/gemma-4-12b-qat")

def is_local_first() -> bool:
    cfg = load_config()
    return cfg.get("local_first", True)

def are_paid_models_enabled() -> bool:
    cfg = load_config()
    return cfg.get("paid_models_enabled", False)

def get_providers() -> dict:
    cfg = load_config()
    return cfg.get("providers", {})

def get_enabled_local_providers() -> list:
    providers = get_providers()
    enabled = []
    for name, data in providers.items():
        if data.get("type") == "local" and data.get("enabled", False):
            enabled.append(name)
    return enabled

def get_enabled_paid_providers() -> list:
    providers = get_providers()
    enabled = []
    for name, data in providers.items():
        if data.get("type") == "paid" and data.get("enabled", False):
            enabled.append(name)
    return enabled
