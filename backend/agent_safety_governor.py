from typing import Dict, Any

class AgentSafetyGovernor:
    def evaluate_action(self, agent: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        tier = agent.get("max_execution_tier", "T2_DRAFT_REMEDIATOR")
        task_class = agent.get("task_class", "")
        title = agent.get("title", "").lower()
        prompt = agent.get("prompt", "").lower()
        
        sandbox_active = context.get("sandbox_active", False)
        human_approved = context.get("human_approved", False)
        
        # Default state
        approval_required = False
        action_allowed = True
        verdict = "DRY_RUN_GO"
        reason = "Safety guidelines satisfied."

        # High risk domain check (financial, legal, medical, family)
        advisory_classes = ["Financial Services", "Legal / Compliance", "Healthcare", "Family & Personal"]
        is_advisory_class = task_class in advisory_classes or any(w in title or w in prompt for w in ["money", "spend", "legal", "health", "diagnose", "marriage"])
        
        if is_advisory_class:
            if not human_approved:
                approval_required = True
                action_allowed = False
                verdict = "BLOCKED_APPROVAL_REQUIRED"
                reason = f"Action belongs to advisory category/domain and requires operator review."

        # Safety Tier checks
        if tier in ["T3_STAGED_WRITER", "T4_CONTROLLED_EXECUTOR", "T5_PRODUCTION_ACTOR"]:
            approval_required = True
            if not human_approved:
                action_allowed = False
                verdict = "BLOCKED_APPROVAL_REQUIRED"
                reason = f"Agent tier '{tier}' requires human approval before write operations."

        if tier == "T4_CONTROLLED_EXECUTOR":
            if not sandbox_active:
                action_allowed = False
                verdict = "FAIL_CLOSED"
                reason = "Tier T4 execution attempted without active sandbox environment."
                
        if tier == "T5_PRODUCTION_ACTOR":
            if not human_approved:
                action_allowed = False
                verdict = "BLOCKED_APPROVAL_REQUIRED"
                reason = "Tier T5 production action requires explicit, signed human approval."

        return {
            "approval_required": approval_required,
            "action_allowed": action_allowed,
            "verdict": verdict,
            "reason": reason
        }
