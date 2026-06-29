from typing import Dict, Any

class EscalationRouter:
    def __init__(self):
        pass

    def evaluate_escalation(self, gap: Dict[str, Any]) -> bool:
        # Escalate to human only if severity is CRITICAL
        return gap.get("severity") == "CRITICAL"
