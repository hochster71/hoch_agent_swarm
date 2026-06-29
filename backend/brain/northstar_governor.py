# northstar_governor.py
from pathlib import Path

class NorthStarGovernor:
    def __init__(self):
        pass

    def check_alignment(self, task_description: str) -> dict:
        # Check if the task aligns with the monetization/revenue goals
        # HAS must optimize for: validated, revenue-producing outcomes from existing assets
        aligned_keywords = ["revenue", "monetization", "offer", "package", "artifact", "delivery", "proof", "audit", "security", "qa", "test", "verification", "sandbox"]
        is_aligned = any(kw in task_description.lower() for kw in aligned_keywords)
        
        # If it is purely speculative or complex without immediate utility, flag it
        unaligned_keywords = ["quantum optimization", "refactoring engine", "architecture replacement", "cloud migration"]
        has_unaligned = any(kw in task_description.lower() for kw in unaligned_keywords)

        if has_unaligned:
            is_aligned = False
            reason = "Task aligns with speculator/drift category (e.g. quantum or architecture rebuilds instead of existing asset optimization)."
        elif is_aligned:
            reason = "Task supports existing asset verification, stabilization, or direct monetization packaging."
        else:
            reason = "Task is generic. Ensure it relates to revenue readiness or production safety."

        return {
            "aligned": is_aligned,
            "reason": reason,
            "governance_status": "PASS" if is_aligned else "WARN"
        }
