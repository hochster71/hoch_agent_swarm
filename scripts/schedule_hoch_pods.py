#!/usr/bin/env python3
"""
scripts/schedule_hoch_pods.py
Compute-Aware HOCH PODS Scheduler.
Assigns pods to the best available compute nodes based on constraints and policies.
"""

import os
import sys
import json
from datetime import datetime, timezone

def get_project_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def evaluate_node_score(pod, node, health):
    """
    Evaluates how well a node fits a pod. Returns (score, reason).
    Higher score is better. Negative score means incompatible.
    """
    # 1. Workload class compatibility (pod domain must be in allowed_workload_classes)
    if pod["domain"] not in node["allowed_workload_classes"]:
        return -100, f"Workload mismatch: pod domain '{pod['domain']}' not allowed on node."
        
    # 2. Check if health data exists and node is online/degraded
    status = health.get("status", "UNKNOWN")
    if status in ["UNKNOWN", "MANUAL_VERIFY_REQUIRED", "DEGRADED"]:
        return -50, f"Node telemetry status is {status} (offline/degraded)."
        
    # 3. Secrets policy: do not assign secret-bearing work if secrets_allowed = false
    pod_secrets = pod.get("secret_access", [])
    if pod_secrets and not node.get("secrets_allowed", False):
        return -200, "Security violation: pod requires secrets but node secrets_allowed is false."

    # 4. Remote execution check: default deny remote execution unless remote_execution_allowed is true
    if node.get("node_type") in ["virtual_private_server", "cloud"] and not node.get("remote_execution_allowed", False):
        return -300, "Security policy: remote execution is disabled for this node."

    # 5. Model availability check
    pod_model = pod.get("allowed_models", [])
    node_models = list(set((health.get("models_detected", []) or []) + (node.get("available_models", []) or [])))
    # Check if there is at least one model match
    model_match = any(m in node_models for m in pod_model)
    if not model_match:
        return -80, f"Model mismatch: node lacks any of the allowed models {pod_model}."

    # 6. Tool availability check
    pod_tools = pod.get("allowed_tools", [])
    node_tools = list(set((health.get("tools_detected", []) or []) + (node.get("available_tools", []) or [])))
    # We check if the node has at least one of the tools or is capable. For strict tools:
    # If the pod specifies allowed tools, let's verify if the node can execute at least one tool
    tool_match = any(t in node_tools for t in pod_tools)
    if pod_tools and not tool_match:
        # Check if node has no tools at all
        return -70, f"Tool mismatch: node lacks required tools {pod_tools}."

    # Calculation of positive score
    score = 0
    
    # Prioritize ONLINE over DEGRADED
    if status == "ONLINE":
        score += 50
    elif status == "DEGRADED":
        score += 20
        
    # Local-first preference
    if node.get("node_id") == "m5-pro-mbp":
        score += 100  # Strong preference for primary control MBP
    elif node.get("node_type") == "physical":
        score += 40   # Preference for local physical nodes
        
    # Tools match count
    matched_tools = [t for t in pod_tools if t in node_tools]
    score += len(matched_tools) * 5

    return score, f"Compatible. Node status: {status}, matched tools: {len(matched_tools)}."

def main():
    print("==================================================")
    print("RUNNING HOCH PODS COMPUTE-AWARE SCHEDULER")
    print("==================================================")
    
    project_root = get_project_root()
    
    # Load files
    registry_file = os.path.join(project_root, "has_live_project_tracker", "data", "hoch_pods_registry.json")
    state_file = os.path.join(project_root, "has_live_project_tracker", "data", "hoch_pods_runtime_state.json")
    nodes_file = os.path.join(project_root, "has_live_project_tracker", "data", "hoch_compute_nodes.json")
    health_file = os.path.join(project_root, "has_live_project_tracker", "data", "hoch_compute_node_health.json")
    queue_file = os.path.join(project_root, "has_live_project_tracker", "data", "revenue_action_queue.json")
    
    files = [registry_file, state_file, nodes_file, health_file, queue_file]
    for f_path in files:
        if not os.path.exists(f_path):
            print(f"[ERROR] Required file missing: {f_path}")
            sys.exit(1)
            
    with open(registry_file, "r") as f:
        pods_registry = json.load(f)
    with open(state_file, "r") as f:
        pods_state = json.load(f)
    with open(nodes_file, "r") as f:
        nodes = json.load(f)
    with open(health_file, "r") as f:
        health_records = json.load(f)
    with open(queue_file, "r") as f:
        actions = json.load(f)

    # Clean stale health data check (Default 600s threshold)
    # Check modification time of health file
    health_mtime = os.path.getmtime(health_file)
    seconds_since_health_update = datetime.now().timestamp() - health_mtime
    is_health_stale = seconds_since_health_update > 600.0
    
    # Check modification time of queue and state file
    queue_mtime = os.path.getmtime(queue_file)
    is_queue_stale = (datetime.now().timestamp() - queue_mtime) > 600.0
    
    state_mtime = os.path.getmtime(state_file)
    is_state_stale = (datetime.now().timestamp() - state_mtime) > 600.0
    
    if is_health_stale:
        print("[WARNING] Compute node health authority data is STALE (>600s). No active workloads will be scheduled.")
    if is_queue_stale:
        print("[WARNING] Upstream Revenue Action Queue is STALE (>600s). Fresh downstream scheduling may be based on stale data.")
    if is_state_stale:
        print("[WARNING] Upstream HOCH PODS Runtime State is STALE (>600s). Fresh downstream scheduling may be based on stale data.")

    schedule = []
    
    for pod in pods_registry:
        pod_id = pod["pod_id"]
        # Find corresponding state
        state_info = next((s for s in pods_state if s["pod_id"] == pod_id), {})
        state_str = state_info.get("state", "DORMANT")
        
        # Check if pod is DORMANT or active
        is_active = state_str != "DORMANT"
        
        assigned_node_id = "None"
        assigned_node_name = "None"
        justification = "Pod is DORMANT. No compute resources allocated."
        status = "DORMANT"
        network_zone = "None"
        secrets_exposed = False
        model_assigned = state_info.get("assigned_model") or (pod["allowed_models"][0] if pod.get("allowed_models") else "None")
        
        # Enforce cloud model label planned/unconfirmed if not explicitly approved
        is_cloud_model = any(cloud in model_assigned.lower() for cloud in ["gpt-", "claude", "gemini"])
        if is_cloud_model:
            approved = pod.get("model_approved", False) or state_info.get("model_approved", False)
            if not approved:
                model_assigned = f"{model_assigned} (planned/unconfirmed)"
                
        tools_required = pod.get("allowed_tools", [])

        if is_active:
            if is_health_stale:
                status = "BLOCKED_COMPUTE"
                justification = "Workload assignment suspended: Node Health Authority telemetry is STALE."
            else:
                # Run scheduling constraints check
                best_score = -9999
                best_node = None
                reject_reasons = {}

                for node in nodes:
                    node_id = node["node_id"]
                    node_health = next((h for h in health_records if h["node_id"] == node_id), {})
                    
                    score, reason = evaluate_node_score(pod, node, node_health)
                    if score >= 0:
                        if score > best_score:
                            best_score = score
                            best_node = (node, reason)
                    else:
                        reject_reasons[node["display_name"]] = reason
                        
                if best_node:
                    node_obj, reason_str = best_node
                    assigned_node_id = node_obj["node_id"]
                    assigned_node_name = node_obj["display_name"]
                    status = "SCHEDULED"
                    justification = f"Assigned to {assigned_node_name}. Reason: {reason_str}"
                    network_zone = node_obj["network_zone"]
                    secrets_exposed = len(pod.get("secret_access", [])) > 0
                else:
                    status = "BLOCKED_COMPUTE"
                    # Collate rejection reasons
                    rejections = "; ".join([f"{k}: {v}" for k, v in reject_reasons.items()])
                    justification = f"Scheduling blocked. Constraints violated on all candidate nodes: {rejections}"
                    
        schedule.append({
            "pod_id": pod_id,
            "pod_name": pod["name"],
            "state": state_str,
            "assigned_node_id": assigned_node_id,
            "assigned_node_name": assigned_node_name,
            "status": status,
            "workload_class": pod["domain"],
            "network_zone": network_zone,
            "secrets_exposed": secrets_exposed,
            "model_assigned": model_assigned,
            "tools_required": tools_required,
            "justification_rationale": justification,
            "last_scheduled_at": datetime.now(timezone.utc).isoformat() + "Z"
        })
        
    # Save schedule output
    schedule_output = os.path.join(project_root, "has_live_project_tracker", "data", "hoch_pod_schedule.json")
    with open(schedule_output, "w") as f:
        json.dump(schedule, f, indent=2)
    print(f"[PASS] Saved pod schedule list to: {schedule_output}")
    
    # Create evidence markdown report
    evidence_dir = os.path.join(project_root, "docs", "evidence", "runtime")
    os.makedirs(evidence_dir, exist_ok=True)
    evidence_file = os.path.join(evidence_dir, "hoch-pod-scheduler-evidence.md")
    
    with open(evidence_file, "w") as f:
        f.write("# HOCH PODS Dynamic Compute Scheduler Evidence\n\n")
        f.write(f"**Scheduler Run Time**: {datetime.now(timezone.utc).isoformat()}Z  \n")
        f.write(f"**Health Telemetry Freshness**: {'STALE (No scheduling)' if is_health_stale else 'FRESH'}  \n\n")
        
        f.write("## Pod Placement Assignments\n\n")
        f.write("| Pod ID | Pod Name | State | Assigned Node | Schedule Status | Workload | Secrets | Rationale |\n")
        f.write("| --- | --- | --- | --- | --- | --- | --- | --- |\n")
        for sc in schedule:
            secrets_indicator = "🔒 YES" if sc["secrets_exposed"] else "✖️ NO"
            f.write(f"| `{sc['pod_id']}` | {sc['pod_name']} | `{sc['state']}` | **{sc['assigned_node_name']}** | **{sc['status']}** | {sc['workload_class']} | {secrets_indicator} | {sc['justification_rationale']} |\n")
            
        f.write("\n## Secure Scheduling Controls Compliance\n")
        f.write("- **Local-First Enforced**: Node preferences favor physical local endpoints.\n")
        f.write("- **Least Privilege Network Routing**: Network zones map directly to the zero-trust microsegmentation design.\n")
        f.write("- **Fail-Closed Compute Blocking**: Any pod matching model/tool/secret policy deficits falls back to `BLOCKED_COMPUTE` instead of cloud execution.\n")
        
    print(f"[PASS] Generated scheduler evidence report: {evidence_file}")
    print("==================================================")

if __name__ == "__main__":
    main()
