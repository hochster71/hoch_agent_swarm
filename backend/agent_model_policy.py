import json
import logging
import hashlib
from backend.runtime_execution_store import (
    now_iso,
    list_model_providers_db,
    get_service_node_leases,
    persist_agent_model_policy_db,
    get_agent_model_policy_db,
    list_agent_model_policies_db,
    log_agent_model_policy_decision_db
)
from backend.inference_gateway import scan_for_secrets

logger = logging.getLogger("AgentModelPolicy")

def init_default_agent_model_policies() -> None:
    """
    Seeds default agent-to-model policies in SQLite database if they do not exist.
    """
    existing = list_agent_model_policies_db()
    if existing:
        logger.info("Agent-to-model policies already initialized.")
        return

    # Seed policies
    defaults = [
        {
            "agent_role": "research",
            "allowed_model_classes": ["reasoning", "general"],
            "preferred_providers": ["provider-14d19eab", "provider-08711bf5"],
            "fallback_providers": ["provider-c25ed87f"],
            "require_trusted_for_sensitive": True,
            "quorum_size": 1,
            "dissent_similarity_threshold": 0.5
        },
        {
            "agent_role": "summarize",
            "allowed_model_classes": ["general"],
            "preferred_providers": ["provider-14d19eab"],
            "fallback_providers": ["provider-08711bf5"],
            "require_trusted_for_sensitive": False,
            "quorum_size": 1,
            "dissent_similarity_threshold": 0.5
        },
        {
            "agent_role": "review",
            "allowed_model_classes": ["reasoning", "coding"],
            "preferred_providers": ["provider-14d19eab", "provider-08711bf5"],
            "fallback_providers": ["provider-c25ed87f"],
            "require_trusted_for_sensitive": True,
            "quorum_size": 1,
            "dissent_similarity_threshold": 0.5
        },
        {
            "agent_role": "approval_assist",
            "allowed_model_classes": ["reasoning"],
            "preferred_providers": ["provider-08711bf5", "provider-c25ed87f"],
            "fallback_providers": ["provider-14d19eab"],
            "require_trusted_for_sensitive": True,
            "quorum_size": 3,
            "dissent_similarity_threshold": 0.70
        }
    ]

    for p in defaults:
        persist_agent_model_policy_db(p)
    logger.info("Successfully seeded default agent-to-model policies.")

def evaluate_agent_model_policy(agent_role: str, task_context: dict) -> dict:
    """
    Evaluates the model routing assignment for a given agent role and task context.
    Checks:
    - Prompt safety (secrets detection)
    - Health & lease status of preferred model providers
    - Fallback strategies
    - High-risk escalations requiring multi-model quorums
    """
    task_id = task_context.get("task_id")
    run_id = task_context.get("run_id")
    prompt = task_context.get("prompt", "")
    risk_level = task_context.get("risk_level", "low").lower()
    
    # 1. Fetch policy for role (fallback to research if not found)
    policy = get_agent_model_policy_db(agent_role)
    if not policy:
        # Generate default policy on the fly
        policy = {
            "agent_role": agent_role,
            "allowed_model_classes": ["general"],
            "preferred_providers": [],
            "fallback_providers": [],
            "require_trusted_for_sensitive": True,
            "quorum_size": 1,
            "dissent_similarity_threshold": 0.5
        }

    # 2. Check for secrets
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest() if prompt else ""
    is_sensitive = False
    if prompt:
        is_sensitive = scan_for_secrets([{"role": "user", "content": prompt}])
        
    require_trusted = policy["require_trusted_for_sensitive"] and is_sensitive
    trusted_enforced = 1 if require_trusted else 0

    # 3. Gather active, approved, healthy model providers
    all_providers = list_model_providers_db()
    leases = {l["node_id"]: l for l in get_service_node_leases()}
    
    eligible_providers = []
    for p in all_providers:
        if not p.get("approved_for_inference"):
            continue
        if p.get("health_status") not in ["available", "degraded"]:
            continue
            
        # Verify node lease if bound
        node_id = p.get("node_id")
        if node_id:
            lease = leases.get(node_id)
            if not lease:
                continue
            if lease.get("availability") in ["sleeping", "offline"]:
                continue
                
        # Sensitivity check
        if require_trusted and not p.get("trusted_for_sensitive_context"):
            continue
            
        # Role check: check if role is supported
        allowed_roles = p.get("allowed_agent_roles", [])
        if allowed_roles and agent_role not in allowed_roles:
            continue
            
        eligible_providers.append(p)

    # 4. Determine Routing Selection
    # If high risk or quorum required, select multiple
    is_high_risk = (risk_level == "high") or (policy["quorum_size"] > 1)
    target_count = policy["quorum_size"] if is_high_risk else 1
    
    selected_pids = []
    policy_status = "enforced"
    reason = "Routed according to operator preferred policy settings."

    # First try preferred list
    for pid in policy["preferred_providers"]:
        match = next((x for x in eligible_providers if x["model_provider_id"] == pid), None)
        if match and pid not in selected_pids:
            selected_pids.append(pid)
            if len(selected_pids) >= target_count:
                break

    # Next try fallbacks
    if len(selected_pids) < target_count:
        policy_status = "fallback"
        reason = "One or more preferred model providers offline. Initiated fallback routing."
        for pid in policy["fallback_providers"]:
            match = next((x for x in eligible_providers if x["model_provider_id"] == pid), None)
            if match and pid not in selected_pids:
                selected_pids.append(pid)
                if len(selected_pids) >= target_count:
                    break

    # If still not enough, grab any remaining eligible provider
    if len(selected_pids) < target_count:
        for p in eligible_providers:
            pid = p["model_provider_id"]
            if pid not in selected_pids:
                selected_pids.append(pid)
                if len(selected_pids) >= target_count:
                    break

    # If no provider could be resolved at all, it fails!
    if not selected_pids:
        policy_status = "failed"
        if require_trusted:
            reason = "Blocked: No trusted model providers are online to handle sensitive context."
        else:
            reason = "Failed: No eligible model providers are online for this agent role."

    # 5. Log decision log to DB
    import uuid
    log_id = f"POL-{uuid.uuid4().hex[:6].upper()}"
    log_payload = {
        "log_id": log_id,
        "task_id": task_id,
        "run_id": run_id,
        "agent_role": agent_role,
        "agent_id": task_context.get("agent_id"),
        "prompt_hash": prompt_hash,
        "policy_status": policy_status,
        "selected_providers": selected_pids,
        "use_multi_model": 1 if is_high_risk and len(selected_pids) > 1 else 0,
        "trusted_enforced": trusted_enforced,
        "reason": reason,
        "logged_at": now_iso()
    }
    log_agent_model_policy_decision_db(log_payload)

    return {
        "policy_status": policy_status,
        "use_multi_model": bool(log_payload["use_multi_model"]),
        "selected_providers": selected_pids,
        "model_class_matched": ", ".join(policy["allowed_model_classes"]),
        "trusted_enforced": bool(trusted_enforced),
        "reason": reason,
        "logged_at": log_payload["logged_at"]
    }
