from typing import Dict, Any, List

class PrintableSummary:
    def __init__(self):
        pass

    def generate(self, query: str, ranked_items: List[Dict[str, Any]], domain: str) -> str:
        lines = []
        lines.append("==================================================")
        lines.append("      HAS OPERATOR BRIEF: SHOPPING RESEARCH")
        lines.append("==================================================")
        lines.append(f"Query:  {query}")
        lines.append(f"Domain: {domain}")
        lines.append("")
        
        lines.append("Ranked Candidates (Safety-First):")
        lines.append("--------------------------------------------------")
        
        for item in ranked_items:
            prod = item["product"]
            screen = item["safety_result"]
            rank = item["rank"]
            
            status_str = "SAFE (PASS)" if screen["passed"] else "BLOCKED (FAIL)"
            lines.append(f"{rank}. {prod['title']}")
            lines.append(f"   Price:      ${prod['price']:.2f}")
            lines.append(f"   Seller:     {prod['seller']}")
            lines.append(f"   Safety:     {status_str}")
            
            if screen["violations"]:
                lines.append("   Violations:")
                for v in screen["violations"]:
                    lines.append(f"     - {v}")
            if screen["warnings"]:
                lines.append("   Warnings:")
                for w in screen["warnings"]:
                    lines.append(f"     - {w}")
                    
            if screen.get("supervision_required"):
                lines.append("   NOTE: Supervised playtime required for this item.")
            lines.append(f"   URL:        {prod['url']}")
            lines.append("")
            
        lines.append("Enforced Policy Constraints:")
        lines.append("  - Purchases and checkouts are HARD BLOCKED at the code level.")
        lines.append("  - All transactions require wallet/payment control plane installation.")
        lines.append("==================================================")
        
        return "\n".join(lines)
