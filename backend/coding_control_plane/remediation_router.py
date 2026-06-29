import yaml
import os
from typing import Dict, Any, List
from backend.coding_control_plane.agent_scoreboard import AgentScoreboard

class RemediationRouter:
    def __init__(self, policy_path: str = "config/agent_scoreboard_policy.yaml"):
        self.policy_path = policy_path
        self.policy = self._load_policy()
        self.scoreboard = AgentScoreboard()

    def _load_policy(self) -> Dict[str, Any]:
        if os.path.exists(self.policy_path):
            with open(self.policy_path, "r") as f:
                return yaml.safe_load(f) or {}
        return {}

    def route_task(self, task_type: str) -> Dict[str, Any]:
        """
        Determines the best agent for a given task type based on scoreboard data.
        Returns selected agent and sandbox requirements.
        """
        scores = self.scoreboard.get_agent_scores()
        matching_agents = [s for s in scores if s.get("task_type") == task_type]

        if not matching_agents:
            # Fallback to general agent
            selected_agent = "Claude Code"
        else:
            # Sort by pass rate descending
            matching_agents.sort(key=lambda a: a.get("pass_rate", 0), reverse=True)
            selected_agent = matching_agents[0]["agent_name"]

        # Look up sandbox requirement
        sandbox_mappings = self.policy.get("agent_scoreboard_policy", {}).get("remediation_allowed_sandbox_levels", {})
        sandbox = sandbox_mappings.get(selected_agent, "High")

        return {
            "task_type": task_type,
            "routed_agent": selected_agent,
            "sandbox_requirement": sandbox
        }
