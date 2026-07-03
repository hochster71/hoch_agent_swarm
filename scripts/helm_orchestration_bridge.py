#!/usr/bin/env python3
import sys
import json
import datetime

def run_bridge():
    queue_path = "has_live_project_tracker/data/mission_intake_queue.json"
    control_path = "has_live_project_tracker/data/orchestration_bridge_control.json"
    task_queue_path = "has_live_project_tracker/data/helm_task_queue.json"
    
    # Read control switch
    try:
        with open(control_path, "r") as f:
            control = json.load(f)
        if not control.get("orchestration_bridge_enabled"):
            print("Bridge disabled via kill switch control file.")
            sys.exit(0)
    except Exception:
        pass

    try:
        with open(queue_path, "r") as f:
            queue_data = json.load(f)
    except Exception:
        print("Intake queue missing.")
        sys.exit(1)

    missions = queue_data.get("missions", [])
    new_missions = [m for m in missions if m.get("status") == "NEW"]
    
    if not new_missions:
        print("No new missions found.")
        sys.exit(0)

    # Load task queue
    try:
        with open(task_queue_path, "r") as f:
            task_queue = json.load(f)
    except Exception:
        task_queue = []

    for mission in new_missions:
        m_id = mission.get("mission_id")
        intent = mission.get("intent")
        
        # Verify signing status
        if mission.get("signature_status") == "UNSIGNED":
            mission["status"] = "REJECTED_UNSIGNED"
            continue
            
        if mission.get("sanitization_status") == "FAIL":
            mission["status"] = "REJECTED_INJECTION"
            continue

        # Decompose
        task_id = f"task-{m_id}-001"
        decomposed_task = {
            "task_id": task_id,
            "mission_id": m_id,
            "task_name": f"Decomposed from {mission.get('title')}",
            "task_class": "planning",
            "risk_tier": mission.get("risk_tier", "R1"),
            "allowed_agent": "hasf_scoring_agent",
            "required_model_tier": "heavy",
            "adapter": "ollama_gpu_pod",
            "expected_output": "docs/evidence/bridge_task_output.md",
            "evidence_required": True,
            "gates_required": ["verify_tier3_routing_policy.py"],
            "founder_approval_required": mission.get("founder_approval_required", False),
            "data_egress_class": "PUBLIC_SAFE",
            "provider_allowed": "openai_reasoning_adapter",
            "cost_policy_ref": "api_budget_policy.json",
            "status": "PENDING"
        }
        
        # Check security override bounds
        if "production_release" in intent or "monetize" in intent:
            if not mission.get("founder_approval_required"):
                mission["status"] = "BLOCKED"
                continue

        task_queue.append(decomposed_task)
        mission["status"] = "DECOMPOSED"
        mission["updated_at"] = datetime.datetime.utcnow().isoformat() + "Z"

    # Save updates
    with open(queue_path, "w") as f:
        json.dump(queue_data, f, indent=2)
        
    with open(task_queue_path, "w") as f:
        json.dump(task_queue, f, indent=2)

    print("🟢 Orchestration bridge run completed.")

if __name__ == "__main__":
    run_bridge()
