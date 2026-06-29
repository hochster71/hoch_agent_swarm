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
    Evaluates agent-to-model routing policies to select the most appropriate
    healthy, approved model provider.
    """
    from backend.agent_model_policy import evaluate_agent_model_policy
    
    # Map agent_id/context to policy role
    agent_role = "research"
    agent_id_lower = (agent_id or "").lower()
    if "summarize" in agent_id_lower or "brief" in agent_id_lower:
        agent_role = "summarize"
    elif "review" in agent_id_lower or "audit" in agent_id_lower or "developer" in agent_id_lower:
        agent_role = "review"
    elif "approve" in agent_id_lower or "gate" in agent_id_lower or "release" in agent_id_lower:
        agent_role = "approval_assist"

    task_context = {
        "task_id": task_id,
        "run_id": options.get("run_id"),
        "prompt": prompt,
        "risk_level": options.get("risk_level", "low"),
        "agent_id": agent_id
    }

    result = evaluate_agent_model_policy(agent_role, task_context)
    if result["policy_status"] == "failed" or not result["selected_providers"]:
        raise ValueError(f"Agent model policy routing failed: {result['reason']}")

    # Return the primary selected provider
    primary_provider_id = result["selected_providers"][0]
    provider = get_model_provider_db(primary_provider_id)
    if not provider:
        raise ValueError(f"Selected model provider '{primary_provider_id}' from policy not found in database.")
        
    return provider


def write_inference_evidence(inference_run_id: str, data: dict) -> str:
    import os
    workspace_root = Path(__file__).resolve().parent.parent
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
