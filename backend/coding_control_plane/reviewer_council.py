from typing import Dict, Any

class ReviewerCouncil:
    def __init__(self):
        pass

    def evaluate_patch_review(self, patching_agent: str, reviewer_agent: str) -> Dict[str, Any]:
        """Strictly ensures that the patching agent is never allowed to approve its own work."""
        if patching_agent == reviewer_agent:
            return {
                "verdict": "REJECTED",
                "reason": f"Self-approval violation: {patching_agent} cannot review their own patch."
            }
        
        return {
            "verdict": "APPROVED",
            "reason": f"Patch created by {patching_agent} has been successfully validated by {reviewer_agent}."
        }
