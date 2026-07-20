"""HERMES — HELM Execution & Routing Model Exchange Service.

Route by CAPABILITY, never by vendor. HERMES is a composition layer over the existing
HELM runtime: it adds worker manifests + worker selection, and reuses HELM's frozen
capability registry, provider router, and the single guarded dispatch choke point.
"""
from backend.hermes.worker_registry import list_workers, get_worker, discover_local, registry_health
from backend.hermes.capability_map import select_worker, workers_for_capability, capability_matrix
from backend.hermes.dispatcher import dispatch, explain
from backend.hermes.learning import record_mission, worker_stats, recommend_worker

__all__ = ["list_workers", "get_worker", "discover_local", "registry_health",
           "select_worker", "workers_for_capability", "capability_matrix",
           "dispatch", "explain", "record_mission", "worker_stats", "recommend_worker"]
