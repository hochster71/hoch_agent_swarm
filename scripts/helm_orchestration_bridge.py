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
        control = {}

    # Rung 3 auto-promotion check
    try:
        with open(queue_path, "r") as f:
            q_data = json.load(f)
        missions_list = q_data.get("missions", [])
        
        log_path = "has_live_project_tracker/data/helm_execution_log.json"
        try:
            with open(log_path, "r") as f:
                logs = json.load(f)
        except Exception:
            logs = []
            
        manual_intervention = any(
            e.get("event") in ["manual_prompt_injected", "manual_review_intervention"] for e in logs
        )
        
        clean_completed = [
            m for m in missions_list 
            if m.get("status") == "COMPLETED" 
            and m.get("signature_status") in ["VALID", "NOT_REQUIRED_DRY_RUN"] 
            and m.get("sanitization_status") == "PASS"
        ]
        
        # If we have at least 3 clean missions and no interventions, promote to Rung 3!
        if len(clean_completed) >= 3 and not manual_intervention:
            if not control.get("allow_ag_execution"):
                control["allow_ag_execution"] = True
                with open(control_path, "w") as f:
                    json.dump(control, f, indent=2)
                print("🟢 Mechanical gate check: Rung 3 promotion requirements met. allow_ag_execution flipped to True.")
    except Exception as e:
        print(f"Drift check or Rung 3 validation error: {e}")

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
