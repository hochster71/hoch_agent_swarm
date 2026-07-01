import json
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

class ToolOpsManager:
    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            base_dir = Path(__file__).resolve().parent.parent
        self.base_dir = base_dir
        self.registry_path = self.base_dir / "data" / "prompt_registry" / "tool_registry.json"
        self.state_path = self.base_dir / "data" / "prompt_registry" / "toolops_state.json"
        self._ensure_files()

    def _ensure_files(self):
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.registry_path.exists():
            # default tools will be created
            pass
        if not self.state_path.exists():
            default_state = {
                "total_tool_calls": 0,
                "blocked_calls": 0,
                "pending_approvals": [],
                "blocked_actions": [],
                "audit_log": []
            }
            self.state_path.write_text(json.dumps(default_state, indent=2), encoding="utf-8")

    def load_tools(self) -> List[Dict[str, Any]]:
        try:
            return json.loads(self.registry_path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def save_tools(self, tools: List[Dict[str, Any]]):
        self.registry_path.write_text(json.dumps(tools, indent=2), encoding="utf-8")

    def load_state(self) -> Dict[str, Any]:
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def save_state(self, state: Dict[str, Any]):
        self.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def authorize_action(
        self,
        tool_id: str,
        agent_role: str,
        prompt_family: str,
        model_id: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        tools = self.load_tools()
        state = self.load_state()
        
        tool = next((t for t in tools if t["tool_id"] == tool_id), None)
        
        # 1. Unknown tool fail-closed guard
        if not tool:
            err_msg = f"UNREGISTERED_TOOL: Tool '{tool_id}' is not registered in ToolOps."
            self._log_blocked(state, tool_id, agent_role, params, "UNREGISTERED_TOOL", err_msg)
            raise ValueError(err_msg)

        if tool.get("status") == "blocked":
            err_msg = f"TOOL_BLOCKED: Tool '{tool_id}' is currently blocked globally."
            self._log_blocked(state, tool_id, agent_role, params, "TOOL_BLOCKED", err_msg)
            raise ValueError(err_msg)

        risk_class = tool.get("risk_class", "read-only")
        
        # 2. Check model trust tier (ModelOps failed_eval blocks privileged/destructive/networked tools)
        from backend.modelops_manager import ModelOpsManager
        modelops = ModelOpsManager(self.base_dir)
        models = modelops.load_models()
        model_record = next((m for m in models if m["model_id"] == model_id), None)
        if model_record and model_record.get("status") == "failed_eval":
            if risk_class in ["destructive", "privileged", "networked", "production-impacting"]:
                err_msg = f"LOW_TRUST_MODEL_BLOCKED: Model '{model_id}' failed evaluation gate. Executing risk class '{risk_class}' is prohibited."
                self._log_blocked(state, tool_id, agent_role, params, "LOW_TRUST_MODEL_BLOCKED", err_msg)
                raise ValueError(err_msg)

        # 3. Check Agent Role Authorization
        allowed_agents = tool.get("allowed_agents", [])
        if "*" not in allowed_agents and agent_role not in allowed_agents:
            err_msg = f"UNAUTHORIZED_AGENT: Agent role '{agent_role}' is not authorized to use tool '{tool_id}'."
            self._log_blocked(state, tool_id, agent_role, params, "UNAUTHORIZED_AGENT", err_msg)
            raise ValueError(err_msg)

        # 4. Check Prompt Family Authorization
        allowed_families = tool.get("allowed_prompt_families", [])
        if "*" not in allowed_families and prompt_family not in allowed_families:
            err_msg = f"UNAUTHORIZED_FAMILY: Prompt family '{prompt_family}' is not authorized to use tool '{tool_id}'."
            self._log_blocked(state, tool_id, agent_role, params, "UNAUTHORIZED_FAMILY", err_msg)
            raise ValueError(err_msg)

        # 5. Check blocked patterns (secret exfiltration / destructive commands)
        param_str = str(params).lower()
        # Scan general exfiltration keywords
        for pattern in ["private_key", "passwd", "ssh-add", "aws_secret", "secret_key"]:
            if pattern in param_str:
                err_msg = f"BLOCKED_EXFILTRATION_PATTERN: Action contains potential secret exfiltration keyword: '{pattern}'."
                self._log_blocked(state, tool_id, agent_role, params, "SECRET_EXFILTRATION_BLOCKED", err_msg)
                raise ValueError(err_msg)

        # Scan tool specific patterns
        for pattern in tool.get("blocked_patterns", []):
            if pattern.lower() in param_str:
                err_msg = f"BLOCKED_PATTERN_DETECTED: Parameter contains prohibited pattern: '{pattern}'."
                self._log_blocked(state, tool_id, agent_role, params, "BLOCKED_PATTERN_DETECTED", err_msg)
                raise ValueError(err_msg)

        # 6. Check destination hosts for networked tools
        if risk_class == "networked" or tool_id == "http_request":
            host = params.get("host") or params.get("url", "")
            if host:
                allowed_hosts = tool.get("allowed_hosts", [])
                matched = any(allowed.lower() in host.lower() for allowed in allowed_hosts)
                if not matched:
                    err_msg = f"UNKNOWN_HOST_BLOCKED: Outbound request to unregistered host '{host}' is prohibited."
                    self._log_blocked(state, tool_id, agent_role, params, "UNKNOWN_HOST_BLOCKED", err_msg)
                    raise ValueError(err_msg)

        # 7. Check Approval Gates for destructive / production-impacting tools
        action_id = str(uuid.uuid4())
        requires_approval = tool.get("requires_approval", False)
        
        if requires_approval:
            # Check if this action ID or command signature has been manually approved
            approved_actions = state.get("approved_actions", {})
            cmd_signature = f"{tool_id}:{param_str}"
            
            if cmd_signature not in approved_actions.values():
                # Not approved. Place in pending_approvals
                pending_item = {
                    "action_id": action_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "tool_id": tool_id,
                    "agent_role": agent_role,
                    "prompt_family": prompt_family,
                    "model_id": model_id,
                    "params": params,
                    "signature": cmd_signature,
                    "risk_class": risk_class,
                    "status": "pending"
                }
                state["pending_approvals"].insert(0, pending_item)
                state["blocked_calls"] = state.get("blocked_calls", 0) + 1
                self.save_state(state)
                err_msg = f"APPROVAL_REQUIRED: Action requires explicit operator approval."
                raise ValueError(err_msg)

        # Action is authorized!
        state["total_tool_calls"] = state.get("total_tool_calls", 0) + 1
        state["audit_log"].insert(0, {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool_id": tool_id,
            "agent_role": agent_role,
            "params": params,
            "verdict": "APPROVED",
            "details": "Action authorized successfully under active governance policies."
        })
        self.save_state(state)
        
        return {
            "action_id": action_id,
            "verdict": "APPROVED",
            "tool_id": tool_id,
            "risk_class": risk_class,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def approve_action(self, action_id: str, operator: str) -> Dict[str, Any]:
        state = self.load_state()
        pending = state.get("pending_approvals", [])
        
        item = next((i for i in pending if i["action_id"] == action_id), None)
        if not item:
            raise ValueError(f"Action request {action_id} not found in pending list.")

        # Remove from pending approvals
        state["pending_approvals"] = [i for i in pending if i["action_id"] != action_id]
        
        # Add to approved actions dict
        if "approved_actions" not in state:
            state["approved_actions"] = {}
        state["approved_actions"][action_id] = item["signature"]

        # Log to audit log
        state["audit_log"].insert(0, {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool_id": item["tool_id"],
            "agent_role": item["agent_role"],
            "params": item["params"],
            "verdict": "OPERATOR_APPROVED",
            "details": f"Override approved by operator '{operator}'."
        })
        self.save_state(state)
        
        return {
            "action_id": action_id,
            "verdict": "APPROVED",
            "operator": operator,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def _log_blocked(self, state: Dict[str, Any], tool_id: str, agent_role: str, params: Dict[str, Any], category: str, details: str):
        state["blocked_calls"] = state.get("blocked_calls", 0) + 1
        blocked_item = {
            "blocked_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool_id": tool_id,
            "agent_role": agent_role,
            "params": params,
            "category": category,
            "details": details
        }
        state["blocked_actions"].insert(0, blocked_item)
        state["audit_log"].insert(0, {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool_id": tool_id,
            "agent_role": agent_role,
            "params": params,
            "verdict": "BLOCKED",
            "details": details
        })
        self.save_state(state)

    def run_ci_gate_check(self) -> Dict[str, Any]:
        tools = self.load_tools()
        errors = []
        
        # Validate that required schema fields are intact
        required_keys = ["tool_id", "risk_class", "requires_approval"]
        for t in tools:
            for k in required_keys:
                if k not in t:
                    errors.append(f"Tool {t.get('tool_id', 'unknown')} is missing required field '{k}'")
            if t.get("risk_class") not in ["read-only", "safe-write", "destructive", "networked", "privileged", "production-impacting"]:
                errors.append(f"Tool {t.get('tool_id')} has invalid risk_class '{t.get('risk_class')}'")

        status = "PASSED" if len(errors) == 0 else "FAILED"
        return {
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "errors": errors
        }
