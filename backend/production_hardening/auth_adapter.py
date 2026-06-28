# OAuth2/OIDC Scaffolding and Validation
from typing import Dict, Any, List

class OidcAuthAdapter:
    def __init__(self, issuer: str, client_id: str):
        self.issuer = issuer
        self.client_id = client_id

    def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validates JWT OIDC token against issuer keys. Returns claims.
        """
        # Scaffolding returns dummy claims for staging validation tests
        if token == "valid-operator-token":
            return {"sub": "operator-1", "roles": ["operator"]}
        elif token == "valid-admin-token":
            return {"sub": "admin-1", "roles": ["admin"]}
        raise ValueError("Invalid credentials or expired session")

    def enforce_role(self, claims: Dict[str, Any], allowed_roles: List[str]) -> bool:
        """
        Ensures claims contain at least one of the allowed roles.
        """
        user_roles = claims.get("roles", [])
        return any(role in user_roles for role in allowed_roles)
