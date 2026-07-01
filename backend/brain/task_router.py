import os
import yaml
import logging

logger = logging.getLogger("TaskRouter")

class TaskRouter:
    def __init__(self, root_dir=None):
        from backend.runtime_paths import project_root
        if root_dir is None:
            root_dir = str(project_root())
        self.registry_path = os.path.join(root_dir, "config/agent_registry.yaml")

    def load_agents(self) -> list:
        if not os.path.exists(self.registry_path):
            return []
        try:
            with open(self.registry_path, "r") as f:
                data = yaml.safe_load(f) or {}
            return data.get("agents", [])
        except Exception as e:
            logger.error(f"Error loading agent registry: {e}")
            return []

    def route_task_to_agent(self, task_name: str) -> dict:
        agents = self.load_agents()
        # Default to qa-agent for testing/builds, code-agent for editing, evidence-agent for evidence
        task_lower = task_name.lower()
        
        target_agent = "code-agent"
        if "test" in task_lower or "playwright" in task_lower or "build" in task_lower:
            target_agent = "qa-agent"
        elif "evidence" in task_lower or "report" in task_lower:
            target_agent = "evidence-agent"
        elif "backup" in task_lower or "snapshot" in task_lower:
            target_agent = "backup-agent"
        elif "docker" in task_lower or "container" in task_lower:
            target_agent = "runtime-agent"
        elif "security" in task_lower or "audit" in task_lower:
            target_agent = "security-agent"
            
        agent = next((a for a in agents if a["id"] == target_agent), None)
        if not agent and agents:
            agent = agents[0]
            
        return agent
