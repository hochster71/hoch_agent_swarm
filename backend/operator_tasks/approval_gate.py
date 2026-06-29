import yaml
import os
from pathlib import Path
from typing import Dict, Any

class ApprovalGate:
    def __init__(self):
        self.config = {}
        config_path = Path("/app/config/purchase_block_policy.yaml") if os.path.exists("/app") else Path(__file__).resolve().parent.parent.parent / "config" / "purchase_block_policy.yaml"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    self.config = yaml.safe_load(f)
        except Exception:
            pass
            
        self.purchase_policy = self.config.get("hard_purchase_blocks", {
            "blocked_actions": [
                "purchase", "checkout", "payment_submission", "saved_payment_change",
                "shipping_address_change", "bitcoin_transfer", "crypto_purchase",
                "stock_trade", "investment_execution", "subscription_signup"
            ],
            "enforcement": {
                "mode": "STRICT",
                "raise_exception_on_violation": True
            }
        })

    def verify_action(self, action_type: str, details: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Verify if an action is allowed. Always blocks payments and checkout actions.
        """
        blocked_actions = self.purchase_policy["blocked_actions"]
        
        if action_type in blocked_actions:
            # Code-level block enforcement
            err_msg = f"CRITICAL SECURITY VIOLATION: Action '{action_type}' is strictly blocked under HAS Purchase Block Policy."
            if self.purchase_policy["enforcement"].get("raise_exception_on_violation", True):
                raise PermissionError(err_msg)
            return {
                "allowed": False,
                "reason": err_msg,
                "action": action_type
            }
            
        return {
            "allowed": True,
            "action": action_type
        }
