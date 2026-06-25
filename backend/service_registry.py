from datetime import datetime, timezone
import json
import logging
from backend.runtime_execution_store import (
    get_discovered_device,
    persist_discovered_device,
    persist_service_node,
    get_service_node,
    delete_service_node
)

logger = logging.getLogger("ServiceRegistry")

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def approve_service_node(node_id: str, operator: str, roles: list[str]) -> bool:
    dev = get_discovered_device(node_id)
    if not dev:
        logger.error(f"Device {node_id} not found in discovery list")
        return False
        
    dev["onboarding_status"] = "approved"
    dev["operator_notes"] = f"Approved by operator {operator} with roles: {', '.join(roles)}"
    persist_discovered_device(dev)
    
    service_node = {
        "node_id": node_id,
        "approved_at": now_iso(),
        "approved_by_operator": operator,
        "display_name": dev["display_name"],
        "device_class": dev["device_class"],
        "fleet_group": dev["fleet_group"],
        "compute_tier": dev["compute_tier"],
        "service_roles": roles,
        "service_endpoints": dev.get("service_endpoints") or [],
        "trusted_compute": True if dev["device_class"] in ("mac", "pc", "linux_host") else False,
        "onboarding_status": "approved",
        "last_seen": now_iso(),
        "health_status": "Active",
        "no_auto_install_guarantee": True
    }
    persist_service_node(service_node)
    
    try:
        from backend.main import cluster_mgr
        cluster_mgr.load_approved_service_nodes()
    except Exception as e:
        logger.error(f"Failed to reload cluster manager topology: {e}")
        
    logger.info(f"Successfully approved service node {node_id}")
    return True

def reject_service_node(node_id: str, operator: str, reason: str) -> bool:
    dev = get_discovered_device(node_id)
    if not dev:
        logger.error(f"Device {node_id} not found in discovery list")
        return False
        
    dev["onboarding_status"] = "rejected"
    dev["operator_notes"] = f"Rejected by operator {operator}. Reason: {reason}"
    persist_discovered_device(dev)
    
    delete_service_node(node_id)
    
    try:
        from backend.main import cluster_mgr
        cluster_mgr.load_approved_service_nodes()
    except Exception as e:
        logger.error(f"Failed to reload cluster manager topology: {e}")
        
    logger.info(f"Successfully rejected service node {node_id}")
    return True
