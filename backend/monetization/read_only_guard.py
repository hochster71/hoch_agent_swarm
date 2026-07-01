import os
import yaml

class ReadOnlyGuard:
    def __init__(self, root_dir=None):
        from backend.runtime_paths import project_root
        if root_dir is None:
            root_dir = str(project_root())
        self.root_dir = root_dir
        self.policy_path = os.path.join(root_dir, "config/monetization_audit_policy.yaml")
        self.allowed_paths = [
            os.path.join(root_dir, "data/monetization/"),
            os.path.join(root_dir, "docs/evidence/monetization/"),
            os.path.join(root_dir, "docs/planning/monetization/")
        ]
        self.prohibited_actions = ["mv", "rm", "rename", "rsync --delete", "git clean", "git reset", "chmod", "chown"]
        self.load_policy()

    def load_policy(self):
        if os.path.exists(self.policy_path):
            with open(self.policy_path, "r") as f:
                data = yaml.safe_load(f) or {}
            policy = data.get("monetization_audit_policy", {})
            raw_paths = policy.get("allowed_write_paths", self.allowed_paths)
            self.allowed_paths = []
            for p in raw_paths:
                if "hoch_agent_swarm" in p:
                    p = p[p.find("hoch_agent_swarm") + len("hoch_agent_swarm"):]
                    if p.startswith("/"):
                        p = p[1:]
                    p = os.path.join(self.root_dir, p)
                self.allowed_paths.append(os.path.abspath(p))
            self.prohibited_actions = policy.get("prohibited_actions", self.prohibited_actions)

    def verify_write_path(self, filepath: str):
        abs_path = os.path.abspath(filepath)
        allowed = False
        for allowed_dir in self.allowed_paths:
            # Ensure folder has trailing separator to avoid partial prefix matching
            clean_dir = os.path.join(allowed_dir, '')
            if abs_path.startswith(clean_dir):
                allowed = True
                break
        if not allowed:
            raise PermissionError(f"Monetization sidecar blocked: Write attempt outside allowed paths at '{abs_path}'")

    def verify_command(self, cmd: str):
        cmd_lower = cmd.lower()
        tokens = cmd_lower.split()
        for action in self.prohibited_actions:
            if " " in action:
                if action in cmd_lower:
                    raise PermissionError(f"Monetization sidecar blocked: Prohibited action '{action}' found in command '{cmd}'")
            else:
                for t in tokens:
                    if t == action or (action in ["rm", "mv"] and t.startswith(action) and len(t) <= 3):
                        raise PermissionError(f"Monetization sidecar blocked: Prohibited action '{action}' found in command '{cmd}'")
                
    def verify_no_mutation(self, file_op: str, src: str, dst: str = None):
        op_lower = file_op.lower()
        if op_lower in ["move", "delete", "rename", "remove", "unlink"]:
            raise PermissionError(f"Monetization sidecar blocked: Prohibited mutating operation '{file_op}' on '{src}'")
