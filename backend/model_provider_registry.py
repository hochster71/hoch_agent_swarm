import json
import time
import urllib.request
import urllib.error
import logging
from backend.runtime_execution_store import (
    now_iso,
    register_model_provider_db,
    update_model_provider_db,
    get_model_provider_db,
    list_model_providers_db,
    delete_model_provider_db
)

logger = logging.getLogger("ModelProviderRegistry")

def list_model_providers() -> list[dict]:
    return list_model_providers_db()

def get_model_provider(model_provider_id: str) -> dict | None:
    return get_model_provider_db(model_provider_id)

def register_model_provider(payload: dict) -> dict:
    model_provider_id = payload.get("model_provider_id")
    if not model_provider_id:
        import uuid
        model_provider_id = f"provider-{uuid.uuid4().hex[:8]}"
    
    # Set default fields
    payload["model_provider_id"] = model_provider_id
    payload.setdefault("health_status", "unverified")
    payload.setdefault("approved_for_inference", False)
    payload.setdefault("trusted_for_sensitive_context", False)
    payload.setdefault("allowed_agent_roles", [])
    payload.setdefault("allowed_task_types", [])
    payload.setdefault("model_ids", [payload.get("default_model")] if payload.get("default_model") else [])
    
    register_model_provider_db(model_provider_id, payload)
    return get_model_provider(model_provider_id)

def update_model_provider(model_provider_id: str, payload: dict) -> dict:
    update_model_provider_db(model_provider_id, payload)
    return get_model_provider(model_provider_id)

def approve_model_provider(model_provider_id: str, operator: str, allowed_roles: list[str], allowed_task_types: list[str]) -> dict:
    now = now_iso()
    notes = f"Approved by operator '{operator}' at {now}."
    payload = {
        "approved_for_inference": True,
        "allowed_agent_roles": allowed_roles,
        "allowed_task_types": allowed_task_types,
        "operator_notes": notes
    }
    update_model_provider_db(model_provider_id, payload)
    return get_model_provider(model_provider_id)

def disable_model_provider(model_provider_id: str, operator: str, reason: str) -> dict:
    now = now_iso()
    notes = f"Disabled by operator '{operator}' at {now}. Reason: {reason}"
    payload = {
        "approved_for_inference": False,
        "operator_notes": notes
    }
    update_model_provider_db(model_provider_id, payload)
    return get_model_provider(model_provider_id)

def health_check_model_provider(model_provider_id: str) -> dict:
    provider = get_model_provider(model_provider_id)
    if not provider:
        raise ValueError(f"Model provider '{model_provider_id}' not found.")
    
    # Determine health check URL
    url = provider.get("health_url") or provider.get("endpoint_url")
    if not url:
        # Manual bridge or unknown URL, cannot health check directly
        update_model_provider_db(model_provider_id, {
            "health_status": "unavailable",
            "last_health_check_at": now_iso(),
            "latency_ms": -1.0
        })
        return get_model_provider(model_provider_id)
    
    # If using /v1/chat/completions as endpoint but health_url is blank, try checking models endpoint
    if not provider.get("health_url") and "/v1/chat/completions" in url:
        url = url.replace("/v1/chat/completions", "/v1/models")
    
    start_time = time.perf_counter()
    status = "unavailable"
    latency = -1.0
    
    try:
        req = urllib.request.Request(url, method="GET")
        req.add_header("User-Agent", "Hoch-Agent-Swarm-HealthCheck")
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                status = "available"
                latency = (time.perf_counter() - start_time) * 1000.0
            else:
                status = "degraded"
                latency = (time.perf_counter() - start_time) * 1000.0
    except Exception as e:
        logger.warning(f"Health check failed for provider '{model_provider_id}' at {url}: {e}")
        status = "unavailable"
    
    update_model_provider_db(model_provider_id, {
        "health_status": status,
        "last_health_check_at": now_iso(),
        "latency_ms": latency
    })
    
    return get_model_provider(model_provider_id)

def discover_models_for_provider(model_provider_id: str) -> list[str]:
    provider = get_model_provider(model_provider_id)
    if not provider:
        raise ValueError(f"Model provider '{model_provider_id}' not found.")
    
    url = provider.get("models_url") or provider.get("endpoint_url")
    if not url:
        return provider.get("model_ids", [])
    
    # Adjust URL based on provider type if not explicitly set
    provider_type = provider.get("provider_type")
    if not provider.get("models_url"):
        if provider_type == "ollama":
            if "/api/chat" in url:
                url = url.replace("/api/chat", "/api/tags")
            elif not url.endswith("/api/tags"):
                url = url.rstrip("/") + "/api/tags"
        else:
            # openai compatible, lm studio, localai, etc.
            if "/v1/chat/completions" in url:
                url = url.replace("/v1/chat/completions", "/v1/models")
            elif not url.endswith("/v1/models"):
                url = url.rstrip("/") + "/v1/models"
    
    try:
        req = urllib.request.Request(url, method="GET")
        req.add_header("User-Agent", "Hoch-Agent-Swarm-ModelDiscovery")
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                models = []
                if provider_type == "ollama":
                    models_list = data.get("models", [])
                    for m in models_list:
                        name = m.get("name") or m.get("model")
                        if name:
                            models.append(name)
                else:
                    data_list = data.get("data", [])
                    for m in data_list:
                        mid = m.get("id")
                        if mid:
                            models.append(mid)
                
                if models:
                    update_model_provider_db(model_provider_id, {
                        "model_ids": models,
                        "default_model": models[0] if provider.get("default_model") not in models else provider.get("default_model")
                    })
                    return models
    except Exception as e:
        logger.warning(f"Model discovery failed for provider '{model_provider_id}' at {url}: {e}")
    
    return provider.get("model_ids", [])
