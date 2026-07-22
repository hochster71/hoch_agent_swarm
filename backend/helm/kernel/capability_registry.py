"""HELM Kernel Capability Registry.

Maintains dynamic capability abstraction bindings for worker allocation.
"""

from typing import Any, Dict, List, Optional, Set


STANDARD_CAPABILITIES = {
    "capability.orchestration": "Task graph decomposition, scheduling, and state coordination",
    "capability.coding": "Multi-file code generation, refactoring, and patch creation",
    "capability.cybersecurity": "Threat modeling, RMF Rev. 5, OSCAL, and security posture scanning",
    "capability.qa_verification": "Automated unit testing, inter-process burn-in, and replay audits",
    "capability.independent_review": "Out-of-band audit, no-fake-green enforcement, and architecture review",
}


class HELMCapabilityRegistry:
    """Dynamic Capability-to-Worker Allocation Registry."""

    def __init__(self):
        self._bindings: Dict[str, Set[str]] = {cap: set() for cap in STANDARD_CAPABILITIES}

    def register_worker_capabilities(self, worker_id: str, capabilities: List[str]) -> List[str]:
        """Registers a worker for specified capability slots."""
        registered = []
        for cap in capabilities:
            if cap in STANDARD_CAPABILITIES:
                self._bindings[cap].add(worker_id)
                registered.append(cap)
        return registered

    def find_workers_for_capabilities(self, required_capabilities: List[str]) -> List[str]:
        """Returns worker IDs that satisfy ALL required capabilities."""
        if not required_capabilities:
            return []

        candidates = None
        for cap in required_capabilities:
            workers = self._bindings.get(cap, set())
            if candidates is None:
                candidates = set(workers)
            else:
                candidates = candidates.intersection(workers)

        return sorted(list(candidates or set()))
