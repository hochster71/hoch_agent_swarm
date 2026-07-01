import os
import json
import logging
import yaml
from datetime import datetime
from backend.agent_runner import AgentRunner

logger = logging.getLogger("BrainOrchestrator")

class BrainOrchestrator:
    def __init__(self, root_dir=None):
        from backend.runtime_paths import project_root
        if root_dir is None:
            root_dir = str(project_root())
        self.root_dir = os.path.abspath(root_dir)
        self.policy_path = os.path.join(self.root_dir, "config/autonomy_policy.yaml")
        self.tracker_path = os.path.join(self.root_dir, "frontend/data/pert_tracker.json")
        self.agent_registry_path = os.path.join(self.root_dir, "frontend/data/agent_registry.json")
        
        self.status = "IDLE"
        self.active_task = None
        self.active_agent = None
        self.approvals = []
        self.audit_trail = ["Brain LLM Orchestrator Initialized."]
        
        self.agent_runner = AgentRunner()

    def get_status(self):
        # Synchronize queue list from pert_tracker
        queue = []
        try:
            if os.path.exists(self.tracker_path):
                with open(self.tracker_path, "r") as f:
                    data = json.load(f)
                queue = [t["id"] for t in data.get("tasks", []) if t.get("status") == "active" or t.get("status") == "planning"]
        except Exception as e:
            logger.error(f"Error loading tracker queue: {e}")

        return {
            "status": self.status,
            "activeTask": self.active_task,
            "activeAgent": self.active_agent,
            "queue": queue,
            "approvals": self.approvals,
            "auditTrail": self.audit_trail
        }

    def load_policies(self):
        if not os.path.exists(self.policy_path):
            return {}
        try:
            with open(self.policy_path, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load policies: {e}")
            return {}

    def tick(self):
        self.audit_trail.append(f"[{datetime.utcnow().isoformat()}Z] Ticking Brain Loop...")
        
        if self.status == "AWAITING_APPROVAL":
            self.audit_trail.append(f"[{datetime.utcnow().isoformat()}Z] Loop BLOCKED: Awaiting operator approval.")
            return self.get_status()

        # Step 1: Read PERT Tracker
        if not os.path.exists(self.tracker_path):
            self.status = "FAILED"
            self.audit_trail.append("Error: pert_tracker.json not found.")
            return self.get_status()

        try:
            with open(self.tracker_path, "r") as f:
                tracker_data = json.load(f)
        except Exception as e:
            self.status = "FAILED"
            self.audit_trail.append(f"Error loading tracker: {str(e)}")
            return self.get_status()

        # Step 2: Select next task from critical path or uncompleted tasks
        critical_path = tracker_data.get("criticalPath", [])
        tasks = tracker_data.get("tasks", [])
        
        next_task = None
        for task_id in critical_path:
            t = next((tk for tk in tasks if tk["id"] == task_id), None)
            if t and t.get("status") != "completed":
                next_task = t
                break
                
        if not next_task:
            # Fallback to any uncompleted task
            for t in tasks:
                if t.get("status") != "completed":
                    next_task = t
                    break

        if not next_task:
            self.status = "COMPLETED"
            self.active_task = None
            self.active_agent = None
            self.audit_trail.append("Mission fully achieved. Zero tasks remaining.")
            return self.get_status()

        # Step 3: Check Authority Policy Matrix
        self.active_task = f"[{next_task['id']}] {next_task['name']}"
        self.active_agent = next_task.get("owner", "Code Agent")
        
        # Check if the task matches any restricted action types
        action_mapping = {
            "T": "production_release",
            "S": "production_release",
            "O": "edit_code"
        }
        action_type = action_mapping.get(next_task["id"], "read_files")
        
        policies = self.load_policies()
        policy = next((p for p in policies.get("policies", []) if p.get("actionType") == action_type), None)
        
        if policy and policy.get("michaelApprovalRequired", False):
            # Block and request approval
            self.status = "AWAITING_APPROVAL"
            request_id = f"req-{next_task['id']}-{int(datetime.utcnow().timestamp())}"
            self.approvals.append({
                "id": request_id,
                "action": action_type,
                "task": next_task["id"],
                "reason": f"Restricted operation '{action_type}' requires commander sign-off."
            })
            self.audit_trail.append(f"[{datetime.utcnow().isoformat()}Z] BLOCKED: Task [{next_task['id']}] triggers restricted action '{action_type}'. Escalating to Michael.")
            return self.get_status()

        # Step 4: Execute task via local LLM query
        self.status = "EXECUTING"
        self.audit_trail.append(f"[{datetime.utcnow().isoformat()}Z] Routing Task [{next_task['id']}] to {self.active_agent}...")
        
        # Simulate local LLM reasoning
        prompt = f"Resolve task: {next_task['name']} for Hoch Agent Swarm."
        completion = self.agent_runner.query_ollama(prompt, model="llama3")
        
        # Step 5: Mark task completed and save
        next_task["status"] = "completed"
        tracker_data["metadata"]["updatedAt"] = datetime.utcnow().isoformat() + "Z"
        
        try:
            with open(self.tracker_path, "w") as f:
                json.dump(tracker_data, f, indent=2)
            self.audit_trail.append(f"[{datetime.utcnow().isoformat()}Z] Task [{next_task['id']}] completed by {self.active_agent}.")
            self.status = "IDLE"
        except Exception as e:
            self.status = "FAILED"
            self.audit_trail.append(f"Failed to update tracker: {str(e)}")

        return self.get_status()

    def approve_action(self, request_id, approval_granted=True):
        req = next((r for r in self.approvals if r["id"] == request_id), None)
        if not req:
            return False, "Request not found."

        self.approvals.remove(req)
        
        if approval_granted:
            self.audit_trail.append(f"[{datetime.utcnow().isoformat()}Z] Operator APPROVED request {request_id}.")
            self.status = "IDLE"
            
            # Execute the blocked task
            try:
                with open(self.tracker_path, "r") as f:
                    tracker_data = json.load(f)
                
                t = next((tk for tk in tracker_data.get("tasks", []) if tk["id"] == req["task"]), None)
                if t:
                    t["status"] = "completed"
                    tracker_data["metadata"]["updatedAt"] = datetime.utcnow().isoformat() + "Z"
                    with open(self.tracker_path, "w") as f:
                        json.dump(tracker_data, f, indent=2)
                    self.audit_trail.append(f"[{datetime.utcnow().isoformat()}Z] Action '{req['action']}' completed for Task [{req['task']}].")
            except Exception as e:
                self.audit_trail.append(f"Error executing approved action: {e}")
        else:
            self.audit_trail.append(f"[{datetime.utcnow().isoformat()}Z] Operator DENIED request {request_id}. Rollback triggered.")
            self.status = "IDLE"
            
        return True, "Success"
