import json
import uuid
import logging
from datetime import datetime
from backend.runtime_execution_store import persist_routing_decision, list_service_nodes

logger = logging.getLogger("CapabilityRouter")

# Static capabilities for core swarm nodes
CORE_NODE_CAPABILITIES = {
    "L1": ["compute", "build", "qa", "automation", "control_plane", "approval_terminal", "mobile_dashboard"],
    "L2": ["compute", "build", "qa", "automation"],
    "L3": ["compute", "build", "qa", "automation"],
    "W1": ["compute", "build", "qa", "automation"],
    "IPAD": ["mobile_dashboard", "approval_terminal"],
    "IPHONE": ["mobile_dashboard"],
    "IPAD_PRO_11": ["mobile_dashboard", "approval_terminal"],
    "IPAD_MINI_1": ["mobile_dashboard", "approval_terminal"],
    "IPAD_MINI_2": ["mobile_dashboard", "approval_terminal"]
}

def extract_required_capabilities(task_type: str, prompt: str, explicit_caps: list[str] = None) -> list[str]:
    """
    Decides what capabilities are required for a task based on explicit parameters,
    task type, or prompt keywords.
    """
    if explicit_caps is not None:
        return explicit_caps

    prompt_lower = prompt.lower()
    req_caps = []

    # Check for display/alert/rendering tasks
    if "display" in prompt_lower or "render" in prompt_lower or "alert" in prompt_lower or "wall" in prompt_lower:
        req_caps.append("display")
        return req_caps

    # Check for spatial/mixed reality/operator console tasks
    if "spatial" in prompt_lower or "operator console" in prompt_lower or "xr" in prompt_lower or "headset" in prompt_lower:
        req_caps.append("spatial")
        return req_caps

    # Check for operator manual approval / signature tasks
    if "approve" in prompt_lower or "sign" in prompt_lower or "override" in prompt_lower or "attestation" in prompt_lower:
        req_caps.append("approval_terminal")
        return req_caps

    # Check for mobile ui dashboard tasks
    if task_type == "mobile" or "mobile" in prompt_lower or "ui dashboard" in prompt_lower:
        req_caps.append("mobile_dashboard")
        return req_caps

    # Default to general compute
    req_caps.append("compute")
    return req_caps

def get_node_capabilities(node_id: str, node_data: dict) -> list[str]:
    """
    Determines the capabilities of a node, whether it's a core node or a dynamically approved service node.
    """
    # 1. Check if it's a core node
    if node_id in CORE_NODE_CAPABILITIES:
        return CORE_NODE_CAPABILITIES[node_id]

    # 2. Check if it's a dynamic service node
    device_class = node_data.get("device_class")
    service_roles = node_data.get("service_roles", [])

    if device_class == "tv_display":
        return ["display"]
    elif device_class == "xr_headset":
        return ["spatial", "operator_console", "voice"]
    elif device_class == "ipad":
        caps = ["mobile_dashboard", "approval_terminal"]
        if "compute_worker" in service_roles:
            caps.append("compute")
        return caps
    elif device_class == "mac" or device_class == "pc":
        return ["compute", "build", "qa", "automation"]
    
    # Untrusted / unapproved / fallback
    return []

def route_task_by_capabilities(task_type: str, prompt: str, explicit_caps: list[str] = None, all_nodes: dict = None) -> dict:
    """
    Evaluates capabilities across all cluster nodes, filters out untrusted/offline targets,
    and returns the selected eligible node data. Records the decision log to SQLite.
    """
    if all_nodes is None:
        all_nodes = {}

    required_caps = extract_required_capabilities(task_type, prompt, explicit_caps)
    routing_decisions = {}
    eligible_nodes = []

    # Load approved service nodes from DB to ensure we match their DB properties
    approved_db_nodes = {n["node_id"]: n for n in list_service_nodes()}

    for nid, ndata in all_nodes.items():
        node_name = ndata.get("name", nid)
        node_status = ndata.get("status", "Active")
        
        # 1. Trust checks
        is_core = nid in CORE_NODE_CAPABILITIES
        is_approved = nid in approved_db_nodes

        if not is_core and not is_approved:
            routing_decisions[nid] = {
                "name": node_name,
                "status": "rejected",
                "reason": "Untrusted or unapproved device candidate.",
                "capabilities": []
            }
            continue

        # 2. Offline checks
        if node_status == "Offline" or ndata.get("latency_ms", 0) == -1:
            routing_decisions[nid] = {
                "name": node_name,
                "status": "rejected",
                "reason": "Device is currently offline.",
                "capabilities": []
            }
            continue

        # Use DB roles/class for approved dynamic devices
        eval_data = ndata
        if is_approved:
            db_node = approved_db_nodes[nid]
            eval_data = {
                "device_class": db_node["device_class"],
                "service_roles": db_node["service_roles"]
            }

        # 3. Capability checks
        caps = get_node_capabilities(nid, eval_data)
        missing = [cap for cap in required_caps if cap not in caps]

        if missing:
            routing_decisions[nid] = {
                "name": node_name,
                "status": "rejected",
                "reason": f"Device class '{eval_data.get('device_class', 'core')}' lacks required capabilities: {', '.join(missing)}.",
                "capabilities": caps
            }
        else:
            routing_decisions[nid] = {
                "name": node_name,
                "status": "eligible",
                "reason": "Device matches all required capabilities.",
                "capabilities": caps
            }
            eligible_nodes.append(nid)

    if not eligible_nodes:
        # Fallback to L1 if default compute, else raise
        if "compute" in required_caps and "L1" in all_nodes:
            selected_nid = "L1"
        else:
            raise ValueError(f"No eligible node found matching required capabilities: {', '.join(required_caps)}")
    else:
        # Select eligible node with lowest CPU usage
        selected_nid = min(eligible_nodes, key=lambda n: all_nodes[n].get("cpu_usage", 100))

    selected_node = all_nodes[selected_nid]
    routing_id = f"RT-{uuid.uuid4().hex[:6].upper()}"

    # Persist decision log
    persist_routing_decision(
        routing_id=routing_id,
        task_type=task_type,
        prompt=prompt,
        required_caps=required_caps,
        selected_node_id=selected_nid,
        selected_node_name=selected_node.get("name", selected_nid),
        eligible_nodes=eligible_nodes,
        routing_decisions=routing_decisions
    )

    logger.info(f"Routed task to {selected_node['name']} ({selected_nid}) via capability match: {required_caps}")
    return selected_node
