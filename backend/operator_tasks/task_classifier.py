import re
from typing import Dict, Any

class TaskClassifier:
    def __init__(self):
        # Classification keywords/regex
        self.patterns = {
            "CHILD_TOYS": re.compile(r"\blego\b|\btoy(?:s)?\b.*\bchild(?:ren)?\b|\bdisney\b|\bplaymobil\b|\bbarbie\b", re.IGNORECASE),
            "PET_TOYS": re.compile(r"\bpet\b|\brat(?:s)?\b|\btoy(?:s)?\b.*\brat(?:s)?\b|\bhamster(?:s)?\b|\btunnel(?:s)?\b|\bchew\b", re.IGNORECASE),
            "CYBER_TOOLS": re.compile(r"\bexploit\b|\bcyber\b|\bhack\b|\bpen-test\b|\bwireshark\b", re.IGNORECASE),
            "ELECTRONICS": re.compile(r"\bphone\b|\bcomputer\b|\blaptop\b|\btv\b|\bheadphones\b|\belectronics\b", re.IGNORECASE),
            "HOUSEHOLD": re.compile(r"\bsoap\b|\bvacuum\b|\bchair\b|\bfurniture\b|\bkitchen\b|\bhousehold\b", re.IGNORECASE),
        }

    def classify(self, query: str) -> Dict[str, Any]:
        domain = "HOUSEHOLD"  # Default fallback
        
        # Check cyber/hack queries for restricted block
        if re.search(r"\bexploit\b|\bmalware\b|\bhacking tool\b", query, re.IGNORECASE):
            domain = "RESTRICTED_BLOCKED"
        else:
            for dom, pattern in self.patterns.items():
                if pattern.search(query):
                    domain = dom
                    break
        
        # Determine mode from query clues
        mode = "RESEARCH_ONLY"
        if "print" in query.lower():
            mode = "RESEARCH_AND_PRINT"
        elif "link" in query.lower() or "url" in query.lower() or "find" in query.lower():
            mode = "RESEARCH_AND_LINK_PREP"
        elif "cart" in query.lower() or "add to" in query.lower():
            mode = "CART_DRAFT_REQUIRES_APPROVAL"
            
        # If purchase is explicitly requested, indicate block
        purchase_blocked = False
        if any(w in query.lower() for w in ["buy", "purchase", "checkout", "pay", "order"]):
            purchase_blocked = True
            
        return {
            "domain": domain,
            "mode": mode,
            "purchase_blocked_indicated": purchase_blocked
        }
