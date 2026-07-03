#!/usr/bin/env python3
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "has_live_project_tracker/data"

def main():
    print("Executing HELM Autonomy Layer Verification...")
    
    queue_file = DATA_DIR / "helm_task_queue.json"
    if not queue_file.exists():
        print("❌ Verification failed: helm_task_queue.json does not exist.")
        sys.exit(1)
        
    with open(queue_file, "r") as f:
        queue = json.load(f)
        
    completed_tasks = [t for t in queue if t["status"] == "completed"]
    if not completed_tasks:
        print("❌ Verification failed: No completed tasks found in queue.")
        sys.exit(1)
        
    log_file = DATA_DIR / "helm_execution_log.json"
    if not log_file.exists():
        print("❌ Verification failed: helm_execution_log.json does not exist.")
        sys.exit(1)
        
    with open(log_file, "r") as f:
        logs = json.load(f)
        
    if not logs:
        print("❌ Verification failed: Execution log is empty.")
        sys.exit(1)
        
    state_file = DATA_DIR / "helm_runtime_state.json"
    if not state_file.exists():
        print("❌ Verification failed: helm_runtime_state.json does not exist.")
        sys.exit(1)
        
    evidence_path = ROOT / "docs/evidence/runtime_scenarios/20260702T222129Z-24-7-autonomy-reset/autonomous-task-proof.md"
    if not evidence_path.exists() or evidence_path.stat().st_size == 0:
        print("❌ Verification failed: Autonomous task proof evidence file is missing or empty.")
        sys.exit(1)
        
    print("🟢 HELM task completion, execution logs, runtime states, and evidence files verified.")
    print("✅ HELM Autonomy Layer verification PASSED.")

if __name__ == "__main__":
    main()
