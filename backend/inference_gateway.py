import json
import time
import hashlib
import urllib.request
import urllib.error
import logging
import re
from pathlib import Path
from backend.runtime_execution_store import (
    now_iso,
    get_model_provider_db,
    list_model_providers_db,
    get_service_node_leases,
    persist_inference_run_db
)

logger = logging.getLogger("InferenceGateway")

SECRET_PATTERNS = [
    r"(?i)api[_-]?key\s*[:=]\s*['\"][a-zA-Z0-9_\-]{16,}['\"]",
    r"(?i)password\s*[:=]\s*['\"][a-zA-Z0-9_\-]{6,}['\"]",
    r"(?i)secret\s*[:=]\s*['\"][a-zA-Z0-9_\-]{8,}['\"]",
    r"(?i)bearer\s+[a-zA-Z0-9_\-\.\~]{16,}",
    r"(?i)token\s*[:=]\s*['\"][a-zA-Z0-9_\-]{8,}['\"]",
    r"-----BEGIN [A-Z]+ PRIVATE KEY-----"
]

def scan_for_secrets(messages: list[dict]) -> bool:
    for msg in messages:
        content = msg.get("content", "")
        for pattern in SECRET_PATTERNS:
            if re.search(pattern, content):
                return True
    return False

def get_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def send_openai_compatible_chat(provider: dict, model: str, messages: list[dict], options: dict) -> dict:
    url = provider["endpoint_url"]
    headers = {"Content-Type": "application/json"}
    if provider.get("api_key_required") and provider.get("api_key_ref"):
        # If API key is trusted/allowed, we can fetch it, e.g. from env, but let's mock/use placeholder if none exists
        import os
        key_val = os.getenv(provider["api_key_ref"], "placeholder-key")
        headers["Authorization"] = f"Bearer {key_val}"
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": options.get("temperature", 0.7),
        "max_tokens": options.get("max_tokens", 1024),
        "stream": False
    }
    
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=30) as response:
        resp_data = json.loads(response.read().decode("utf-8"))
        # Standard OpenAI extraction
        choices = resp_data.get("choices", [])
        if not choices:
            raise ValueError(f"OpenAI compatible response choice is empty: {resp_data}")
        content = choices[0]["message"]["content"]
        usage = resp_data.get("usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
        return {
            "content": content,
            "usage": usage,
            "raw": resp_data
        }

def send_ollama_chat(provider: dict, model: str, messages: list[dict], options: dict) -> dict:
    url = provider["endpoint_url"]
    if not url.endswith("/api/chat") and not url.endswith("/v1/chat/completions"):
        url = url.rstrip("/") + "/api/chat"
        
    payload = {
        "model": model,
        "messages": messages,
        "options": {
            "temperature": options.get("temperature", 0.7),
            "num_predict": options.get("max_tokens", 1024)
        },
        "stream": False
    }
    
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as response:
        resp_data = json.loads(response.read().decode("utf-8"))
        content = resp_data["message"]["content"]
        return {
            "content": content,
            "usage": {
                "prompt_tokens": resp_data.get("prompt_eval_count", 0),
                "completion_tokens": resp_data.get("eval_count", 0),
                "total_tokens": resp_data.get("prompt_eval_count", 0) + resp_data.get("eval_count", 0)
            },
            "raw": resp_data
        }

def send_lm_studio_chat(provider: dict, model: str, messages: list[dict], options: dict) -> dict:
    return send_openai_compatible_chat(provider, model, messages, options)

def send_localai_chat(provider: dict, model: str, messages: list[dict], options: dict) -> dict:
    return send_openai_compatible_chat(provider, model, messages, options)

def route_inference_request(
    agent_id: str,
    task_id: str,
    required_capabilities: list[str],
    prompt: str,
    options: dict
) -> dict:
    """
    Finds the best eligible, approved, healthy model provider based on:
    - Provider approved_for_inference = True
    - Health status is available/degraded
    - allowed_agent_roles contains agent_id or agent role
    - allowed_task_types contains task type
    - lease is fresh (for device-bound providers)
    - sensitive prompts only sent to trusted providers
    """
    providers = list_model_providers_db()
    leases = {l["node_id"]: l for l in get_service_node_leases()}
    
    messages = [{"role": "user", "content": prompt}]
    has_secrets = scan_for_secrets(messages)
    
    # Infer task type from capabilities or options
    task_type = options.get("task_type")
    if not task_type and required_capabilities:
        task_type = required_capabilities[0]
    
    eligible = []
    for p in providers:
        if not p["approved_for_inference"]:
            continue
        if p["health_status"] not in ["available", "degraded"]:
            continue
        
        # Check sensitive context trust
        if has_secrets and not p["trusted_for_sensitive_context"]:
            continue
            
        # Check task type matching
        if task_type and p["allowed_task_types"]:
            if task_type not in p["allowed_task_types"]:
                continue
                
        # Check agent role matching
        if agent_id and p["allowed_agent_roles"]:
            if agent_id not in p["allowed_agent_roles"]:
                # Also check roles/substrings if agent_id is longer
                matched_role = False
                for role in p["allowed_agent_roles"]:
                    if role in agent_id.lower():
                        matched_role = True
                        break
                if not matched_role:
                    continue
        
        # Check device lease freshness
        if p["node_id"]:
            lease = leases.get(p["node_id"])
            if not lease:
                continue
            if lease["availability"] in ["sleeping", "offline"]:
                continue
            try:
                from datetime import datetime
                last_seen_dt = datetime.fromisoformat(lease["last_seen"].replace("Z", "+00:00"))
                now_dt = datetime.now(last_seen_dt.tzinfo)
                if (now_dt - last_seen_dt).total_seconds() > lease["lease_duration_seconds"]:
                    continue
            except Exception:
                continue
        
        eligible.append(p)
        
    if not eligible:
        raise ValueError("No eligible, approved, and healthy model providers found matching the request criteria.")
        
    # Select provider with lowest latency or first available
    eligible.sort(key=lambda x: x.get("latency_ms", 9999.0))
    return eligible[0]

def write_inference_evidence(inference_run_id: str, data: dict) -> str:
    import os
    workspace_root = Path("/Users/michaelhoch/.gemini/antigravity/scratch/hoch-agent-swarm")
    evidence_dir = workspace_root / "artifacts" / "inference"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    
    evidence_path = evidence_dir / f"{inference_run_id}.json"
    
    # Do not save full prompt/response texts in the evidence to respect sensitive context guidelines
    evidence_data = {
        "inference_run_id": inference_run_id,
        "model_provider_id": data.get("model_provider_id"),
        "node_id": data.get("node_id"),
        "agent_id": data.get("agent_id"),
        "task_id": data.get("task_id"),
        "model_id": data.get("model_id"),
        "prompt_hash": data.get("prompt_hash"),
        "prompt_preview": data.get("prompt_preview"),
        "response_hash": data.get("response_hash"),
        "response_preview": data.get("response_preview"),
        "status": data.get("status"),
        "latency_ms": data.get("latency_ms"),
        "token_usage": data.get("token_usage"),
        "created_at": data.get("created_at"),
        "completed_at": data.get("completed_at"),
        "safety_flags": {
            "secrets_detected": data.get("secrets_detected", False),
            "trusted_context": data.get("trusted_context", False)
        }
    }
    
    with open(evidence_path, "w", encoding="utf-8") as f:
        json.dump(evidence_data, f, indent=2)
        
    return str(evidence_path)
