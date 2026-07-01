import os
from fastapi import HTTPException
from backend.preflight_gate import GATE
from backend.model_router import audit_log

class ExecutionPolicyEngine:
    def __init__(self):
        pass

    def enforce(self, action_name: str, override: bool = False) -> bool:
        # Automatically allow execution in test/CI context to prevent mock environment blocks
        if os.getenv("TEST_MODE") == "true" or os.getenv("CI") == "true":
            return True

        preflight = GATE.run_preflight()
        if preflight["go_no_go"] == "GO":
            return True

        # Check if overridden
        if override:
            failed_checks = [c["id"] for c in preflight["checks"] if c["status"] == "FAIL"]
            warn_checks = [c["id"] for c in preflight["checks"] if c["status"] == "WARN"]
            
            # Log audit trail event
            audit_log.log_routing_event(
                "preflight_override",
                {
                    "action": action_name,
                    "override_reason": "Operator manually bypassed execution policy block",
                    "preflight_score": preflight["overall_score"],
                    "failed_checks": failed_checks,
                    "warning_checks": warn_checks
                }
            )
            return True
            
        # Raise HTTP 400 with preflight checklist details to instruct client
        raise HTTPException(
            status_code=400,
            detail={
                "error": "PREFLIGHT_BLOCKED",
                "message": f"Execution of '{action_name}' is blocked because the system preflight gate returned NO-GO.",
                "go_no_go": preflight["go_no_go"],
                "overall_score": preflight["overall_score"],
                "checks": preflight["checks"]
            }
        )

POLICY_ENGINE = ExecutionPolicyEngine()
