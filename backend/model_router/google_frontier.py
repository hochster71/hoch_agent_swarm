import os
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from backend.runtime_process import RuntimeProcessBus, RuntimeProcessType, RuntimeProcessState
from backend.model_router.escalation_policy import load_escalation_config

class GoogleFrontierException(Exception):
    pass

def load_approvals() -> dict:
    p = Path(__file__).parent.parent.parent / "config" / "escalation_approvals.json"
    if not p.exists():
        return {"approvals": []}
    try:
        return json.loads(p.read_text("utf-8"))
    except Exception:
        return {"approvals": []}

def call_google_frontier(
    model: str,
    prompt: str,
    reason_code: str,
    approval_id: str,
    task_id: str = None,
    agent_id: str = None
) -> str:
    bus = RuntimeProcessBus()
    # 1. Require escalation enabled & policy check
    esc_cfg = load_escalation_config()
    policy = esc_cfg.get("escalation", {})
    if not policy.get("enabled", False):
        raise GoogleFrontierException("Escalation is disabled globally.")
        
    gf_cfg = esc_cfg.get("google_frontier", {})
    if not gf_cfg.get("enabled", False):
        raise GoogleFrontierException("Google frontier escalation is disabled.")

    # 2. Check environment variable
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        bus.emit(
            RuntimeProcessType.GOOGLE_FRONTIER_CALL,
            RuntimeProcessState.FAILED,
            "Google API Call Failed: Missing GOOGLE_API_KEY.",
            agent_id=agent_id,
            task_id=task_id,
            provider="google_gemini",
            model=model,
            escalation_used=True,
            metadata={"error": "Missing GOOGLE_API_KEY"}
        )
        raise GoogleFrontierException("Google API call failed: Missing GOOGLE_API_KEY in environment.")

    # 3. Check reason_code
    allowed_reasons = policy.get("allowed_reasons", [])
    if reason_code not in allowed_reasons:
        raise GoogleFrontierException(f"Reason code '{reason_code}' not in allowed reasons.")

    # 4. Check approval_id in queue
    approvals_data = load_approvals()
    matched = None
    now = datetime.now(timezone.utc).isoformat()
    for app in approvals_data.get("approvals", []):
        if app.get("approval_id") == approval_id:
            expires_at = app.get("expires_at")
            if expires_at and expires_at < now:
                bus.emit(
                    RuntimeProcessType.ESCALATION_DENIED,
                    RuntimeProcessState.DENIED,
                    f"Escalation denied: approval {approval_id} expired.",
                    agent_id=agent_id,
                    task_id=task_id,
                    provider="google_gemini",
                    model=model,
                    escalation_used=True,
                )
                raise GoogleFrontierException("Escalation approval has expired.")
            if app.get("status") != "APPROVED":
                raise GoogleFrontierException("Escalation approval is not APPROVED.")
            matched = app
            break

    if not matched:
        raise GoogleFrontierException(f"Escalation approval '{approval_id}' not found.")

    # 5. Check allowed models
    allowed_models = gf_cfg.get("allowed_models", [])
    if model not in allowed_models:
        raise GoogleFrontierException(f"Model '{model}' is not in allowed escalation models.")

    # 6. Check budget constraints
    max_single_call = gf_cfg.get("max_single_call_usd", 1.0)
    est_cost = 0.25
    if est_cost > max_single_call:
        raise GoogleFrontierException("Estimated cost exceeds max single call budget.")

    # 6.5. Data Egress Policy Check
    from backend.model_router.router import check_data_egress_policy
    if not check_data_egress_policy(prompt, "google_gemini"):
        raise GoogleFrontierException("Data egress block: sensitive content cannot be sent to google_gemini.")

    # 7. Check payload safety: look for blocked payload classes or high risk keywords
    blocked_classes = gf_cfg.get("blocked_payload_classes", [])
    high_risk_keywords = policy.get("high_risk_keywords", [])
    prompt_lower = prompt.lower()
    for kw in high_risk_keywords:
        if kw in prompt_lower:
            raise GoogleFrontierException(f"Payload safety block: high risk keyword '{kw}' detected.")

    # Emit call start event
    bus.emit(
        RuntimeProcessType.GOOGLE_FRONTIER_CALL,
        RuntimeProcessState.RUNNING,
        f"Google Frontier escalation call initiated for model: {model}",
        agent_id=agent_id,
        task_id=task_id,
        provider="google_gemini",
        model=model,
        escalation_used=True,
        metadata={"approval_id": approval_id, "reason_code": reason_code}
    )

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        req_data = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}]
        }).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10.0) as res:
            res_data = json.loads(res.read().decode("utf-8"))
            candidates = res_data.get("candidates", [])
            text_output = ""
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    text_output = parts[0].get("text", "")
            
            bus.emit(
                RuntimeProcessType.GOOGLE_FRONTIER_CALL,
                RuntimeProcessState.COMPLETE,
                "Google Frontier escalation call completed successfully.",
                agent_id=agent_id,
                task_id=task_id,
                provider="google_gemini",
                model=model,
                escalation_used=True,
                metadata={"cost_usd": est_cost}
            )
            return text_output
    except Exception as e:
        bus.emit(
            RuntimeProcessType.GOOGLE_FRONTIER_CALL,
            RuntimeProcessState.FAILED,
            f"Google Frontier call failed: {e}",
            agent_id=agent_id,
            task_id=task_id,
            provider="google_gemini",
            model=model,
            escalation_used=True,
        )
        raise GoogleFrontierException(f"Google Frontier API call failed: {e}")
