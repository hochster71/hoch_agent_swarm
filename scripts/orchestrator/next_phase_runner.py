#!/usr/bin/env python3
import sys
import os
import json
import subprocess
from verify_no_drift import check_drift
from gatekeeper import check_policy
from render_phase_prompt import render_prompt
from write_phase_report import write_report

def get_current_branch():
    res = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True)
    return res.stdout.strip()

def run_loop():
    print("==================================================")
    print("STARTING EVIDENCE-GATED PHASE ORCHESTRATOR LOOP")
    print("==================================================")
    
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # 1. Verify Current Branch
    current_branch = get_current_branch()
    state_path = os.path.join(base_dir, "control/phase_state.json")
    with open(state_path, "r") as f:
        state = json.load(f)
    
    expected_branch = state.get("current_branch_expected")
    if current_branch != expected_branch:
        print(f"[orchestrator] FAIL: Active branch '{current_branch}' does not match expected '{expected_branch}'")
        sys.exit(1)
    print(f"[orchestrator] Active branch verified: {current_branch}")

    # 2. Run No-Drift Check
    try:
        check_drift()
    except SystemExit:
        print("[orchestrator] FAIL: Loop aborted due to drift detection!")
        sys.exit(1)

    # 3. Load next phase info
    registry_path = os.path.join(base_dir, "control/phase_registry.json")
    with open(registry_path, "r") as f:
        registry = json.load(f)
        
    next_phase = registry.get("next_phase")
    print(f"[orchestrator] Next phase to process: {next_phase}")

    # 4. Render prompt template
    prompt_file, prompt_content = render_prompt(next_phase)

    # 5. Run Gatekeeper Validation
    try:
        check_policy(prompt_content)
    except SystemExit:
        print("[orchestrator] FAIL: Gatekeeper blocked prompt generation!")
        sys.exit(1)

    # 6. Write final status reports
    write_report(
        phase=next_phase,
        drift_check_result="PASS",
        rendered_prompt_path=f"artifacts/orchestrator/generated-prompts/{next_phase}.md",
        authority_gate_result="PASS",
        blocked_actions_confirmed=True,
        next_required_human_action=f"Review and paste rendered prompt for {next_phase}"
    )

    print("==================================================")
    print("ORCHESTRATOR LOOP RUN COMPLETED SUCCESSFULLY")
    print("==================================================")

if __name__ == "__main__":
    run_loop()
