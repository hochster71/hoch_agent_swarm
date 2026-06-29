import os
import yaml
import logging

logger = logging.getLogger("AutonomyPolicy")

class AutonomyPolicy:
    def __init__(self, root_dir="/Users/michaelhoch/hoch_agent_swarm"):
        self.policy_path = os.path.join(root_dir, "config/autonomy_policy.yaml")

    def load_policies(self) -> dict:
        if not os.path.exists(self.policy_path):
            return {}
        try:
            with open(self.policy_path, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load policy config: {e}")
            return {}

    def is_action_allowed(self, action_type: str) -> tuple:
        """
        Returns (is_allowed, requires_approval, description)
        """
        data = self.load_policies()
        policies = data.get("policies", [])
        
        policy = next((p for p in policies if p.get("actionType") == action_type), None)
        if not policy:
            # Fail closed on unknown actions
            return False, True, f"Unknown action type: {action_type}. Blocked by default."

        allowed = policy.get("brainLlmAllowed", False)
        requires_approval = policy.get("michaelApprovalRequired", True)
        description = policy.get("description", "")
        
        return allowed, requires_approval, description
