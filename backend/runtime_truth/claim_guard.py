class ClaimGuard:
    def __init__(self):
        pass
        
    def verify_claim(self, claim: str, evidence: list) -> bool:
        # Require evidence and non-empty parameters
        if not claim or not evidence:
            return False
        return True
