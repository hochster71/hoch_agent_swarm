import yaml
from pathlib import Path

ESCALATION_PATH = Path(__file__).parent.parent.parent / "config" / "escalation.yaml"

def load_escalation_config() -> dict:
    if not ESCALATION_PATH.exists():
        return {
            "escalation": {
                "enabled": False,
                "require_human_approval": True,
                "daily_budget_usd": 0,
                "monthly_budget_usd": 0,
                "allowed_reasons": [],
                "blocked_task_types": [],
                "high_risk_keywords": []
            }
        }
    try:
        with open(ESCALATION_PATH, "r") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Error loading escalation config: {e}")
        return {
            "escalation": {
                "enabled": False,
                "require_human_approval": True,
                "daily_budget_usd": 0,
                "monthly_budget_usd": 0,
                "allowed_reasons": [],
                "blocked_task_types": [],
                "high_risk_keywords": []
            }
        }

def check_escalation_policy(task_type: str, prompt: str, reason: str = None) -> dict:
    cfg_data = load_escalation_config()
    policy = cfg_data.get("escalation", {})
    
    # 1. Is escalation enabled?
    if not policy.get("enabled", False):
        return {
            "allowed": False,
            "recommended": False,
            "requires_approval": False,
            "reason": "Escalation disabled by config."
        }
        
    # 2. Check budgets
    if policy.get("daily_budget_usd", 0) <= 0 or policy.get("monthly_budget_usd", 0) <= 0:
        return {
            "allowed": False,
            "recommended": False,
            "requires_approval": False,
            "reason": "Escalation blocked: budget cap is 0."
        }
        
    # 3. Check blocked task types
    blocked_types = policy.get("blocked_task_types", [])
    if task_type in blocked_types:
        return {
            "allowed": False,
            "recommended": False,
            "requires_approval": False,
            "reason": f"Escalation blocked: task type '{task_type}' is prohibited."
        }
        
    # 4. Check high risk keywords
    high_risk_keywords = policy.get("high_risk_keywords", [])
    prompt_lower = prompt.lower()
    found_keywords = [kw for kw in high_risk_keywords if kw.lower() in prompt_lower]
    
    # 5. Check allowed reasons
    allowed_reasons = policy.get("allowed_reasons", [])
    if reason and reason not in allowed_reasons:
        return {
            "allowed": False,
            "recommended": False,
            "requires_approval": False,
            "reason": f"Escalation blocked: reason '{reason}' is not in the allowed list."
        }
        
    # 6. Does it require human approval?
    requires_approval = policy.get("require_human_approval", True) or bool(found_keywords)
    
    keyword_reason = f" (High-risk keywords found: {', '.join(found_keywords)})" if found_keywords else ""
    return {
        "allowed": True,
        "recommended": True,
        "requires_approval": requires_approval,
        "reason": f"Escalation allowed by policy.{keyword_reason}"
    }
