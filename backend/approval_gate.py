import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

class ApprovalGate:
    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            base_dir = Path(__file__).parent.parent
        self.base_dir = base_dir
        self.queue_dir = self.base_dir / "artifacts" / "approvals"
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        self.queue_file = self.queue_dir / "queue.json"
        self.decisions_dir = self.queue_dir / "decisions"
        self.decisions_dir.mkdir(parents=True, exist_ok=True)
        self.init_queue()

    def init_queue(self):
        if not self.queue_file.exists():
            self.queue_file.write_text(json.dumps({"approvals": []}, indent=2), encoding="utf-8")

    def load_queue(self) -> List[Dict[str, Any]]:
        try:
            data = json.loads(self.queue_file.read_text(encoding="utf-8"))
            return data.get("approvals", [])
        except Exception:
            return []

    def save_queue(self, approvals: List[Dict[str, Any]]):
        self.queue_file.write_text(json.dumps({"approvals": approvals}, indent=2), encoding="utf-8")

    def create_request(self, task_description: str, route_plan: Dict[str, Any]) -> Dict[str, Any]:
        task_lower = task_description.lower()
        risk_level = route_plan.get("risk_level", "LOW")
        
        approval_required = route_plan.get("human_approval_required", False)
        
        # Hard check for approval requirements
        if risk_level in ["HIGH", "CRITICAL", "FAIL_CLOSED"]:
            approval_required = True
        elif any(kw in task_lower for kw in [
            "deploy", "publish", "delete", "spend", "app store", "app-store", "firewall", "router", 
            "secrets", "credentials", "family/private data", "family", "private data", "production", 
            "external", "network", "model deletion", "security posture", "bypass approval", "ignore security", 
            "unresolved ambiguity"
        ]):
            approval_required = True

        status = "PENDING"
        if risk_level == "FAIL_CLOSED" or any(f in route_plan.get("fail_closed_triggers", []) for f in ["BYPASS_APPROVAL_ATTEMPTED", "DESTRUCTIVE_UNAUTHORIZED_ACTION"]):
            status = "FAIL_CLOSED"

        approval_reason = "Required due to high risk or restricted action keywords."
        if risk_level == "FAIL_CLOSED":
            approval_reason = "FAIL-CLOSED: Unauthorized bypass or critical safety policy breach."

        approval_id = f"app-{uuid.uuid4().hex[:8]}"
        created_at = datetime.now(timezone.utc).isoformat()

        approval_object = {
            "approval_id": approval_id,
            "created_at": created_at,
            "status": status,
            "requested_by": "prompt_router",
            "mission_type": route_plan.get("mission_type", "AMBIGUOUS"),
            "risk_level": risk_level,
            "task_description": task_description,
            "selected_prompt_ids": route_plan.get("selected_prompt_ids", []),
            "selected_prompt_titles": route_plan.get("selected_prompt_titles", []),
            "approval_reason": approval_reason,
            "blocked_actions": route_plan.get("blocked_actions", []),
            "evidence_required": [
                "approval_gate_report.json",
                f"decision_{approval_id}.json"
            ],
            "decision_by": "Michael Hoch",
            "decision_at": None,
            "decision_note": None,
            "execution_allowed_after_approval": False
        }

        queue = self.load_queue()
        queue.append(approval_object)
        self.save_queue(queue)

        # Write QA report
        self.write_report(approval_object)
        return approval_object

    def record_decision(self, approval_id: str, status: str, note: Optional[str] = None,
                        founder_signature: Optional[str] = None,
                        founder_decision_at: Optional[str] = None) -> Dict[str, Any]:
        queue = self.load_queue()
        target_approval = None
        for app in queue:
            if app["approval_id"] == approval_id:
                target_approval = app
                break

        if not target_approval:
            raise ValueError(f"Approval ID {approval_id} not found.")

        # FAIL_CLOSED approvals cannot be approved
        if target_approval["status"] == "FAIL_CLOSED" and status == "APPROVED":
            raise ValueError("FAIL_CLOSED approvals cannot be approved into execution.")

        target_approval["status"] = status
        target_approval["decision_at"] = founder_decision_at or datetime.now(timezone.utc).isoformat()
        target_approval["decision_note"] = note
        target_approval["execution_allowed_after_approval"] = False

        # FAIL-CLOSED (C2): an APPROVED decision is only recorded with a valid
        # founder signature over the canonical payload. Anything else is rejected.
        if status == "APPROVED":
            from backend.mission_control.founder_signer import verify_approval
            if not founder_signature or not verify_approval(target_approval, founder_signature):
                raise ValueError(
                    "APPROVED decisions require a valid founder signature "
                    "(sign with scripts/founder_approve.py). Recording refused; fail-closed."
                )
            target_approval["founder_signature"] = founder_signature
            target_approval["founder_verified"] = True

        self.save_queue(queue)

        decision_file = self.decisions_dir / f"decision_{approval_id}.json"
        decision_file.write_text(json.dumps(target_approval, indent=2), encoding="utf-8")

        # Write QA report
        self.write_report(target_approval)
        return target_approval

    def get_telemetry(self) -> Dict[str, Any]:
        queue = self.load_queue()
        pending_count = sum(1 for app in queue if app["status"] == "PENDING")
        approved_count = sum(1 for app in queue if app["status"] == "APPROVED")
        denied_count = sum(1 for app in queue if app["status"] == "DENIED")
        deferred_count = sum(1 for app in queue if app["status"] == "DEFERRED")
        
        state = "LIVE"
        if any(app["status"] == "FAIL_CLOSED" for app in queue):
            state = "FAIL_CLOSED"
        elif pending_count > 0:
            state = "PENDING"

        return {
            "state": state,
            "pending_count": pending_count,
            "approved_count": approved_count,
            "denied_count": denied_count,
            "deferred_count": deferred_count,
            "execution_enabled": False
        }

    def write_report(self, approval_object: Dict[str, Any]):
        report_dir = self.base_dir / "artifacts" / "qa" / "approval_gate"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / "approval_gate_report.json"
        
        report = {
            "last_action": "create_or_update",
            "approval": approval_object,
            "telemetry": self.get_telemetry()
        }
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

_gate_instance = None

def get_approval_gate() -> ApprovalGate:
    global _gate_instance
    if _gate_instance is None:
        _gate_instance = ApprovalGate()
    return _gate_instance
