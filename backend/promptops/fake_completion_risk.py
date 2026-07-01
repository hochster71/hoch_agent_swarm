import re
import yaml
import os

class FakeCompletionRisk:
    def __init__(self, terms_path=None):
        if terms_path is None:
            if os.path.exists("/app"):
                terms_path = "/app/config/fake_completion_terms.yaml"
            else:
                terms_path = os.path.join(os.path.dirname(__file__), "../../config/fake_completion_terms.yaml")
                
        self.terms = []
        if os.path.exists(terms_path):
            try:
                with open(terms_path, "r") as f:
                    self.terms = yaml.safe_load(f).get("blacklisted_terms", [])
            except Exception:
                pass
                
        if not self.terms:
            self.terms = [
                "production ready", "complete", "done", "fully autonomous", 
                "no blockers", "100%", "verified", "go", "clean", "secure", 
                "e2e", "all", "best", "everything"
            ]

    def detect_risk(self, prompt_text: str) -> dict:
        text_lower = prompt_text.lower()
        flagged = []
        
        for term in self.terms:
            if term in text_lower:
                # Check if it is tied to gates/evidence in the prompt
                has_gates = "gate" in text_lower or "evidence" in text_lower or "proof" in text_lower
                if not has_gates:
                    flagged.append(term)
                    
        if len(flagged) >= 3:
            risk = "HIGH"
        elif len(flagged) >= 1:
            risk = "MEDIUM"
        else:
            risk = "LOW"
            
        return {
            "risk_level": risk,
            "flagged_terms": flagged,
            "has_claim_controls": "prevent fake" in text_lower or "fake-completion" in text_lower
        }
