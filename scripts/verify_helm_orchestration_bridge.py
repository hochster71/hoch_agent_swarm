#!/usr/bin/env python3
import os
import sys
import json

def verify_bridge():
    required_files = [
        "has_live_project_tracker/data/mission_intake_queue.json",
        "scripts/submit_mission.py",
        "scripts/helm_orchestration_bridge.py",
        "has_live_project_tracker/data/provider_adapter_registry.json",
        "scripts/openai_reasoning_adapter.py",
        "scripts/claude_critic_adapter.py",
        "docs/architecture/AG_EXECUTION_ADAPTER_CONTRACT.md",
        "has_live_project_tracker/data/orchestration_bridge_control.json"
    ]
    
    for file in required_files:
        if not os.path.exists(file):
            print(f"❌ Verification failed: Required file {file} is missing.")
            sys.exit(1)

    # Check tracker copy_paste_required is present
    tracker_path = "has_live_project_tracker/data/has_runtime_state.json"
    try:
        with open(tracker_path, "r") as f:
            tracker = json.load(f)
        if "copy_paste_required_computed" not in tracker:
            print("❌ Verification failed: copy_paste_required_computed is not present in tracker.")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        sys.exit(1)

    print("🟢 HELM Orchestration Bridge verification PASSED.")
    return True

if __name__ == "__main__":
    verify_bridge()
