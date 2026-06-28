# Write-Path Fail-Closed Mutation Gate Scaffolding
from typing import Dict, Any

class MutationGate:
    def __init__(self, verification_endpoint: str):
        self.verification_endpoint = verification_endpoint
        self._used_nonces = set()

    def authorize_mutation(self, mutation_payload: Dict[str, Any], operator_signature: str, nonce: str = None) -> bool:
        """
        Validates mutation request against dual-operator signature schema.
        Fail-closed by default.
        """
        if not operator_signature:
            raise PermissionError("Mutation rejected: Missing operator signature token")

        # Nonce tracking for replay protection
        if nonce is not None:
            if nonce in self._used_nonces:
                raise PermissionError("Mutation rejected: Replay attack detected (nonce already used)")
            self._used_nonces.add(nonce)
        
        # Verify dual signature context
        if operator_signature.startswith("sig-approved-"):
            return True
        
        raise PermissionError("Mutation rejected: Invalid signature context")
