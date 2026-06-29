import os
import json
import logging

logger = logging.getLogger("MissionQueue")

class MissionQueue:
    def __init__(self, root_dir="/Users/michaelhoch/hoch_agent_swarm"):
        self.tracker_path = os.path.join(root_dir, "frontend/data/pert_tracker.json")

    def get_next_pert_task(self) -> dict:
        if not os.path.exists(self.tracker_path):
            return None
        try:
            with open(self.tracker_path, "r") as f:
                data = json.load(f)
            
            critical_path = data.get("criticalPath", [])
            tasks = data.get("tasks", [])
            
            for task_id in critical_path:
                t = next((tk for tk in tasks if tk["id"] == task_id), None)
                if t and t.get("status") != "completed":
                    return t
                    
            for t in tasks:
                if t.get("status") != "completed":
                    return t
        except Exception as e:
            logger.error(f"Error reading mission queue pert tracker: {e}")
        return None
