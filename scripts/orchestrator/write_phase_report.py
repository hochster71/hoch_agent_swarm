#!/usr/bin/env python3
import sys
import os
import json
from datetime import datetime

def write_report(phase, drift_check_result, rendered_prompt_path, authority_gate_result, blocked_actions_confirmed, next_required_human_action):
    print(f"[write_phase_report] Writing report for phase {phase}...")
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    reports_dir = os.path.join(base_dir, "artifacts/orchestrator/reports")
    os.makedirs(reports_dir, exist_ok=True)
    
    report_data = {
      "phase": phase,
      "timestamp": datetime.utcnow().isoformat() + "Z",
      "drift_check_result": drift_check_result,
      "rendered_prompt_path": rendered_prompt_path,
      "authority_gate_result": authority_gate_result,
      "blocked_actions_confirmed": blocked_actions_confirmed,
      "next_required_human_action": next_required_human_action
    }
    
    report_file = os.path.join(reports_dir, f"{phase}_orchestrator_report.json")
    with open(report_file, "w") as f:
        json.dump(report_data, f, indent=2)
        
    print(f"[write_phase_report] PASS: Orchestrator report written to {report_file}")
    return report_file

if __name__ == "__main__":
    # Example execution args
    if len(sys.argv) < 2:
        print("Usage: write_phase_report.py <phase_name>")
        sys.exit(1)
    write_report(sys.argv[1], "PASS", "artifacts/orchestrator/generated-prompts/PR14.md", "PASS", True, "Staging validation review")
