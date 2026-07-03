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

    # Run regression fixture tests
    import subprocess
    
    # 1. Zero History
    res = subprocess.run([
        "python3", "scripts/compute_copy_paste_required.py",
        "--queue", "tests/fixtures/copy_paste/fixture_zero_history/mission_intake_queue.json",
        "--tracker", "tests/fixtures/copy_paste/fixture_zero_history/has_runtime_state.json"
    ], capture_output=True, text=True)
    if "Computed copy_paste_required: True" not in res.stdout:
        print("❌ Verification failed: Zero history fixture did not return copy_paste_required=true.")
        sys.exit(1)
        
    # 2. Manual Injected
    res = subprocess.run([
        "python3", "scripts/compute_copy_paste_required.py",
        "--queue", "tests/fixtures/copy_paste/fixture_manual_injected/mission_intake_queue.json",
        "--log", "tests/fixtures/copy_paste/fixture_manual_injected/helm_execution_log.json",
        "--tracker", "tests/fixtures/copy_paste/fixture_manual_injected/has_runtime_state.json"
    ], capture_output=True, text=True)
    if "Computed copy_paste_required: True" not in res.stdout:
        print("❌ Verification failed: Manual injected fixture did not return copy_paste_required=true.")
        sys.exit(1)
        
    # 3. Clean Mission
    res = subprocess.run([
        "python3", "scripts/compute_copy_paste_required.py",
        "--queue", "tests/fixtures/copy_paste/fixture_clean_mission/mission_intake_queue.json",
        "--log", "tests/fixtures/copy_paste/fixture_clean_mission/helm_execution_log.json",
        "--tracker", "tests/fixtures/copy_paste/fixture_clean_mission/has_runtime_state.json"
    ], capture_output=True, text=True)
    if "Computed copy_paste_required: False" not in res.stdout:
        print("❌ Verification failed: Clean mission fixture did not return copy_paste_required=false.")
        sys.exit(1)

    print("🟢 HELM Orchestration Bridge verification PASSED.")
    return True

if __name__ == "__main__":
    verify_bridge()
