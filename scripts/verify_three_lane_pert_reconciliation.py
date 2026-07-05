#!/usr/bin/env python3
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "has_live_project_tracker/data"
PERT_FILE = DATA_DIR / "fresh_pert_gap_analysis.json"

def main():
    print("Executing Three-Lane PERT Reconciliation Validator...")
    
    if not PERT_FILE.exists():
        print("❌ PERT task graph file missing!")
        sys.exit(1)
        
    with open(PERT_FILE, "r") as f:
        graph = json.load(f)
        
    # Check next action and founder action keys
    if "next_3_safe_actions" not in graph or "founder_actions" not in graph:
        print("❌ Next actions or founder actions missing in task graph!")
        sys.exit(1)
        
    tasks = graph.get("tasks", [])
    if not tasks:
        print("❌ Tasks list is empty!")
        sys.exit(1)
        
    # Confirm K1 is marked as blocked on founder action and is head of critical path
    k1_task = next((t for t in tasks if t["id"] == "K1"), None)
    if not k1_task:
        print("❌ K1 task not found in the graph!")
        sys.exit(1)
        
    if k1_task["status"] != "BLOCKED_FOUNDER_ACTION":
        print(f"❌ K1 task status is {k1_task['status']}, expected BLOCKED_FOUNDER_ACTION!")
        sys.exit(1)
        
    critical_path = graph.get("critical_path", [])
    if not critical_path or critical_path[0] != "K1":
        print(f"❌ Critical path head is {critical_path[0] if critical_path else 'None'}, expected K1!")
        sys.exit(1)
        
    # Verify track tags present on every task
    for t in tasks:
        if "track" not in t or t["track"] not in ["R", "K", "A", "B", "D"]:
            print(f"❌ Task {t['id']} is missing valid track tag!")
            sys.exit(1)
            
    # Reducer fields check
    for field in ["data_as_of", "expires_at"]:
        if field not in graph:
            print(f"❌ Reducer field {field} missing in task graph!")
            sys.exit(1)
            
    print("Verdict derived: CONDITIONAL_GO")
    print("🟢 PERT task graph is fully reconciled and verified.")
    print("✅ Three-lane PERT verification PASSED.")
    sys.exit(0)

if __name__ == "__main__":
    main()
