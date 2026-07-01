import os
import yaml
from typing import Dict, Any
from backend.coding_control_plane.agent_scoreboard import AgentScoreboard

class CodingAgentRouter:
    def __init__(self, scoreboard: AgentScoreboard = None):
        self.scoreboard = scoreboard or AgentScoreboard()

    def route_defect(self, task_type: str) -> Dict[str, Any]:
        best_agent = self.scoreboard.get_best_agent(task_type)
        
        # Resolve sandbox environment based on agent power level
        sandbox_required = False
        if best_agent in ["Claude Code", "Cursor", "Aider", "Codex CLI"]:
            sandbox_required = True

        return {
            "assigned_agent": best_agent,
            "task_type": task_type,
            "sandbox_required": sandbox_required,
            "routing_status": "ROUTED"
        }
