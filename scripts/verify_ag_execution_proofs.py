#!/usr/bin/env python3
import os
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "has_live_project_tracker/data"
QUEUE_FILE = DATA_DIR / "helm_task_queue.json"
PROOF_INDEX_FILE = DATA_DIR / "ag_execution_proof_index.json"

def main():
    print("Executing AG Execution Proofs Verification...")
    
    if not QUEUE_FILE.exists():
        print("❌ Verification failed: helm_task_queue.json does not exist.")
        sys.exit(1)
        
    with open(QUEUE_FILE, "r", encoding="utf-8") as f:
        queue = json.load(f)
        
    completed_tasks = [
        t for t in queue 
        if t.get("status") == "completed" and (t.get("allowed_agent") == "hasf_builder_agent" or t.get("adapter") == "ag_execution_adapter")
    ]
    
    if not completed_tasks:
        print("🟢 No completed autonomous tasks found to verify proofs.")
        print("✅ AG Execution Proofs verification PASSED.")
        sys.exit(0)
        
    for task in completed_tasks:
        task_id = task.get("task_id")
        proof_path = ROOT / f"docs/evidence/runtime/ag_execution_proof_{task_id}.md"
        
        if not proof_path.exists():
            print(f"❌ Verification failed: Proof file missing for completed task {task_id}: {proof_path}")
            sys.exit(1)
            
        content = proof_path.read_text(encoding="utf-8")
        
        # Verify required tags/fields
        required_fields = [
            f"* **Task ID**: {task_id}",
            "* **Lease ID**: lease-",
            "* **Input Hash**: ",
            "* **Output Hash**: ",
            "* **Policy Verdict**: ",
            "* **Doctrine Verdict**: GO"
        ]
        
        for field in required_fields:
            if field not in content:
                print(f"❌ Verification failed: Proof file for task {task_id} is missing required field '{field}'.")
                sys.exit(1)
                
        print(f"  [PASS] Verified proof integrity for task {task_id}")
        
    print("🟢 All completed task proofs have been verified successfully.")
    print("✅ AG Execution Proofs verification PASSED.")
    sys.exit(0)

if __name__ == "__main__":
    main()
