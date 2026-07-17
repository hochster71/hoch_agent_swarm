"""HELM Executive Runtime substrate — platform engines (not actor roles).

Engines:
  - Mission Runtime   coordination, ownership, versioned mission commits
  - Runtime Truth     derived projections (mission_state, external, hmai)
  - Governance        founder gates, field ownership, constitution checks
  - Event Bus         digital nervous system (append-only events)

Truth is derived. Actors are Founder / Orchestrator / Builder / Auditor only.
"""
from backend.helm_runtime.event_bus import publish_event, Event
from backend.helm_runtime.transaction import MissionTransaction, commit_proposal
from backend.helm_runtime.mission_runtime import load_mission, mission_projection_hint
from backend.helm_runtime.mission_store import (
    read_mission,
    current_version,
    read_for_update,
    commit,
    compare_and_swap,
)
from backend.helm_runtime.provider_router import (
    resolve_worker,
    list_workers,
    worker_health,
)
from backend.helm_runtime.role_router import route_proposal, routing_status
from backend.helm_runtime.capability_registry import (
    route_capability,
    roles_for_capability,
    all_capabilities,
)
from backend.helm_runtime.dispatch_gateway import (
    DispatchGateway,
    DispatchRequest,
    DispatchNotEnabledError,
    ProviderAdapter,
    default_gateway,
)

__all__ = [
    "publish_event",
    "Event",
    "MissionTransaction",
    "commit_proposal",
    "load_mission",
    "mission_projection_hint",
    # Bridge — optimistic-concurrency store
    "read_mission",
    "current_version",
    "read_for_update",
    "commit",
    "compare_and_swap",
    # Bridge — worker-as-plugin
    "resolve_worker",
    "list_workers",
    "worker_health",
    # Bridge — the single door
    "route_proposal",
    "routing_status",
    # Capability routing (brand-agnostic)
    "route_capability",
    "roles_for_capability",
    "all_capabilities",
    # Dispatch Gateway (EDR-0002 skeleton — fail-closed)
    "DispatchGateway",
    "DispatchRequest",
    "DispatchNotEnabledError",
    "ProviderAdapter",
    "default_gateway",
]
