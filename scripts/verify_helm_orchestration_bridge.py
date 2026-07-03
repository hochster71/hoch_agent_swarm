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

    # Enforce Rung 2 promotion checks if allow_provider_api_calls is True
    control_path = "has_live_project_tracker/data/orchestration_bridge_control.json"
    with open(control_path, "r") as f:
        control = json.load(f)
    
    evidence_path = "docs/evidence/runtime_scenarios/20260702T222129Z-24-7-autonomy-reset/helm-rung-1-promotion-evidence.md"
    if os.path.exists(evidence_path):
        with open(evidence_path, "r") as f:
            evidence_content = f.read()
        
        import re
        clean_match = re.search(r"Completed Clean Missions:\s*(\d+)", evidence_content)
        esc_match = re.search(r"Escalated Missions:\s*(\d+)", evidence_content)
        total_match = re.search(r"Total Processed Missions:\s*(\d+)", evidence_content)
        
        if clean_match and esc_match:
            clean_count = int(clean_match.group(1))
            esc_count = int(esc_match.group(1))
            
            # Verify clean count excludes escalated
            if "ESCALATED_TO_FOUNDER" in evidence_content:
                # Count occurrences of completed status vs escalated status
                completed_status_count = len(re.findall(r"\|\s*COMPLETED\s*\|", evidence_content))
                escalated_status_count = len(re.findall(r"\|\s*ESCALATED_TO_FOUNDER\s*\|", evidence_content))
                
                # Check for repeated mission deduction
                repeated_status_count = len(re.findall(r"NO_INCREMENT_REPEATED_MISSION", evidence_content))
                expected_clean = completed_status_count - repeated_status_count
                
                if clean_count != expected_clean:
                    print(f"❌ Verification failed: Clean mission count ({clean_count}) does not match expected unique completed clean missions ({expected_clean}).")
                    sys.exit(1)
                if esc_count != escalated_status_count:
                    print("❌ Verification failed: Escalated mission count is inconsistent with the mission history table.")
                    sys.exit(1)

        if control.get("allow_provider_api_calls", False) or "Promotion Criteria Met: 🟢 YES" in evidence_content:
            if not clean_match or int(clean_match.group(1)) < 3:
                print("❌ Verification failed: Fewer than required clean completed missions exist in promotion evidence.")
                sys.exit(1)
            
        if not re.search(r"manual_prompt_injected\s*count.*0", evidence_content.lower()):
            print("❌ Verification failed: Manual prompt injections are not zero in evidence.")
            sys.exit(1)
                
        if not re.search(r"unauthorized\s*task\s*count.*0", evidence_content.lower()):
            print("❌ Verification failed: Unauthorized tasks detected or not marked as 0.")
            sys.exit(1)

        if not re.search(r"provider\s*api\s*call\s*count.*0", evidence_content.lower()):
            print("❌ Verification failed: Provider API calls detected during Rung 1.")
            sys.exit(1)
            
        if not re.search(r"ag\s*execution\s*count.*0", evidence_content.lower()):
            print("❌ Verification failed: AG execution detected during Rung 1.")
            sys.exit(1)
            
        if not re.search(r"copy_paste_required.*false", evidence_content.lower()):
            print("❌ Verification failed: copy_paste_required has not flipped to false by derivation.")
            sys.exit(1)

    print("🟢 HELM Orchestration Bridge verification PASSED.")
    return True

if __name__ == "__main__":
    verify_bridge()
