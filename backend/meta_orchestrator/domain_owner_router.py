from typing import Dict, Any
from backend.meta_orchestrator.domain_registry import DomainRegistry

class DomainOwnerRouter:
    def __init__(self, registry: DomainRegistry):
        self.registry = registry

    def route_to_owner(self, domain_id: str) -> str:
        domain = self.registry.get_domain(domain_id)
        if domain:
            return domain.get("owner_agent", "unassigned")
        return "unassigned"
