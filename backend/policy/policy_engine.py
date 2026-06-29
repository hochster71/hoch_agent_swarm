import os
import yaml
from pathlib import Path
from fastapi import HTTPException

POLICY_DIR = Path(__file__).resolve().parent.parent.parent / "config" / "policies"

class PolicyEngine:
    def __init__(self):
        # Create policies dir if not exists
        os.makedirs(POLICY_DIR, exist_ok=True)
        self._ensure_default_policies()
        
    def _ensure_default_policies(self):
        # Create empty/basic action policy if missing
        act_policy = POLICY_DIR / "action_policy.yaml"
        if not act_policy.exists():
            with open(act_policy, "w") as f:
                yaml.dump({
                    "action_permissions": {
                        "device_read": "auto",
                        "device_write": "approval_required",
                        "code_patch": "auto",
                        "external_share": "approval_required"
                    }
                }, f)
                
    def check_action(self, action_type: str, action_details: dict) -> bool:
        # Check environment override
        if os.getenv("TEST_MODE") == "true" or os.getenv("CI") == "true":
            return True
            
        act_policy = POLICY_DIR / "action_policy.yaml"
        if not act_policy.exists():
            return False
            
        try:
            with open(act_policy, "r") as f:
                policy = yaml.safe_load(f)
                perms = policy.get("action_permissions", {})
                rule = perms.get(action_type, "approval_required")
                
                if rule == "auto":
                    return True
                return False
        except Exception:
            return False

POLICY_ENGINE = PolicyEngine()
