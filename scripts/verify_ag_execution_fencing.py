#!/usr/bin/env python3
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "has_live_project_tracker/data"
QUEUE_FILE = DATA_DIR / "helm_task_queue.json"
PROOF_INDEX_FILE = DATA_DIR / "ag_execution_proof_index.json"
FENCING_STATUS_FILE = DATA_DIR / "ag_execution_fencing_status.json"

def main():
    print("Executing AG Lease Fencing Verification...")
    
    proof_index = {}
    if PROOF_INDEX_FILE.exists():
        with open(PROOF_INDEX_FILE, "r") as f:
            proof_index = json.load(f)
            
    proofs = proof_index.get("proofs", [])
    
    # Check monotonicity
    last_token = 0
    monotonic = True
    for p in proofs:
        tok = p.get("fencing_token", 0)
        if tok < last_token:
            print(f"❌ Fencing token monotonicity violation: token {tok} is smaller than previous {last_token}")
            monotonic = False
        last_token = tok

    # Cross-check queue status
    queue = []
    if QUEUE_FILE.exists():
        with open(QUEUE_FILE, "r") as f:
            queue = json.load(f)
            
    queue_mismatch = False
    for task in queue:
        t_id = task.get("task_id")
        if task.get("status") == "completed" and (task.get("allowed_agent") == "hasf_builder_agent" or task.get("adapter") == "ag_execution_adapter"):
            q_token = task.get("fencing_token")
            # Find in proofs
            match = next((p for p in proofs if p["task_id"] == t_id), None)
            if match:
                p_token = match.get("fencing_token")
                if q_token != p_token:
                    print(f"❌ Fencing token mismatch for task {t_id}: queue token={q_token}, proof token={p_token}")
                    queue_mismatch = True # Actually mismatch but let's log it.
            
    verdict = "PASS" if (monotonic and not queue_mismatch) else "FAIL"
    
    status_payload = {
        "monotonic": monotonic,
        "queue_mismatch": queue_mismatch,
        "verdict": verdict
    }
    
    with open(FENCING_STATUS_FILE, "w") as f:
        json.dump(status_payload, f, indent=2)
        
    if verdict == "FAIL":
        print("❌ AG Lease Fencing verification failed.")
        sys.exit(1)
        
    print("🟢 AG Lease Fencing verification succeeded.")
    print("✅ AG Lease Fencing verification PASSED.")
    sys.exit(0)

if __name__ == "__main__":
    main()
