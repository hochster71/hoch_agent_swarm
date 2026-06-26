import time
import urllib.request
import json
from backend.model_router import model_registry, confidence, escalation_policy, audit_log
from backend.runtime_process import RuntimeProcessBus, RuntimeProcessType, RuntimeProcessState

runtime_bus = RuntimeProcessBus()

class RouterException(Exception):
    pass

def try_local_provider(provider_name: str, model_name: str, prompt: str) -> str:
    """
    Attempts to call local provider (LM Studio or Ollama).
    If offline, raises RouterException.
    """
    providers = model_registry.get_providers()
    if provider_name not in providers:
        raise RouterException(f"Provider {provider_name} not configured.")
        
    p_data = providers[provider_name]
    if not p_data.get("enabled", False):
        raise RouterException(f"Provider {provider_name} is disabled.")
        
    base_url = p_data.get("base_url")
    api_style = p_data.get("api_style")
    
    # Simple HTTP check to simulate local model call
    # We will try fetching the models or endpoint to see if it is live
    # If not live, we fail closed
    try:
        if api_style == "ollama":
            # Call Ollama API
            url = f"{base_url}/api/generate"
            req_data = json.dumps({
                "model": model_name,
                "prompt": prompt,
                "stream": False
            }).encode("utf-8")
            req = urllib.request.Request(
                url, 
                data=req_data, 
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=1.5) as res:
                body = json.loads(res.read().decode("utf-8"))
                return body.get("response", "")
        elif api_style == "openai_compatible":
            # Call OpenAI compatible LM Studio
            url = f"{base_url}/chat/completions"
            req_data = json.dumps({
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False
            }).encode("utf-8")
            req = urllib.request.Request(
                url, 
                data=req_data, 
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=1.5) as res:
                body = json.loads(res.read().decode("utf-8"))
                choices = body.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "")
                return ""
        else:
            raise RouterException(f"Unsupported API style: {api_style}")
    except Exception as e:
        raise RouterException(f"Local provider {provider_name} unreachable: {e}")

def route_and_run(
    prompt: str, 
    task_type: str = "general", 
    preferred_model: str = None, 
    caller_tier: str = "ALPHA", 
    caller_node: str = "macbook-pro-l1", 
    rationale: str = ""
) -> dict:
    local_first = model_registry.is_local_first()
    paid_enabled = model_registry.are_paid_models_enabled()
    
    # Resolve provider and model
    provider = model_registry.get_default_provider()
    model = model_registry.get_default_model()
    
    if preferred_model:
        # Scan providers to see if preferred model is supported
        found = False
        for p_name, p_data in model_registry.get_providers().items():
            if preferred_model in p_data.get("models", []):
                provider = p_name
                model = preferred_model
                found = True
                break
    
    # 1. Determine escalation policy posture
    # (Checking what would happen if we need to escalate)
    esc_status = escalation_policy.check_escalation_policy(task_type, prompt)
    
    output = ""
    local_success = False
    paid_escalation_used = False
    
    # 2. Execute local model if local_first is True
    if local_first:
        # Before local model call: emit MODEL_ROUTE RUNNING
        runtime_bus.emit(
            RuntimeProcessType.MODEL_ROUTE,
            RuntimeProcessState.RUNNING,
            "Routing task to local model provider.",
            provider=provider,
            model=model,
            escalation_used=False,
            metadata={"local_first": True},
        )
        try:
            output = try_local_provider(provider, model, prompt)
            local_success = True
        except RouterException as local_err:
            # If local failure: emit MODEL_ROUTE FAILED
            runtime_bus.emit(
                RuntimeProcessType.MODEL_ROUTE,
                RuntimeProcessState.FAILED,
                "All local model routes failed. Paid escalation remains blocked unless explicitly approved.",
                requires_approval=True,
                escalation_used=False,
                metadata={"errors": str(local_err)},
            )
            # Local failed. Check if we can escalate to paid cloud AI
            if paid_enabled and esc_status.get("allowed", False):
                # Simulate paid model escalation
                output = f"[Escalated to cloud model OpenAI/gpt-5.5 due to: {local_err}] Run output simulated."
                paid_escalation_used = True
            else:
                # Fail closed
                audit_payload = {
                    "provider": provider,
                    "model": model,
                    "task_type": task_type,
                    "caller_tier": caller_tier,
                    "caller_node": caller_node,
                    "error": "No local model providers reachable and paid escalation is disabled.",
                    "paid_escalation_attempted": False,
                    "success": False
                }
                audit_log.log_routing_event("route_failed_closed", audit_payload)
                raise RouterException(
                    "No local model providers reachable, paid escalation disabled, no paid API call attempted."
                )
    
    # 3. Evaluate confidence
    conf = confidence.evaluate_confidence(output)
    
    # After confidence scoring: emit MODEL_ROUTE COMPLETE
    runtime_bus.emit(
        RuntimeProcessType.MODEL_ROUTE,
        RuntimeProcessState.COMPLETE,
        "Local model route completed.",
        provider=provider,
        model=model,
        confidence_score=conf.get("score"),
        escalation_used=paid_escalation_used,
        metadata={"confidence_label": conf.get("label")},
    )
    
    # If confidence is low, emit ESCALATION_RECOMMENDED
    if conf.get("score", 0.0) < 0.7:
        runtime_bus.emit(
            RuntimeProcessType.ESCALATION_RECOMMENDED,
            RuntimeProcessState.APPROVAL_REQUIRED,
            "Local confidence insufficient. Escalation recommended but not executed without approval.",
            provider=provider,
            model=model,
            confidence_score=conf.get("score"),
            requires_approval=True,
            escalation_used=False,
        )

    # 4. Write audit log
    audit_payload = {
        "provider": provider,
        "model": model,
        "task_type": task_type,
        "caller_tier": caller_tier,
        "caller_node": caller_node,
        "success": True,
        "paid_escalation_used": paid_escalation_used,
        "confidence_score": conf.get("score"),
        "confidence_label": conf.get("label")
    }
    audit_written = audit_log.log_routing_event("route_success", audit_payload)
    
    return {
        "provider": provider,
        "model": model,
        "output": output,
        "confidence": conf,
        "escalation": esc_status,
        "local_first": local_first,
        "paid_escalation_used": paid_escalation_used,
        "audit_event_written": audit_written
    }
