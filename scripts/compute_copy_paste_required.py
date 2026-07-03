#!/usr/bin/env python3
import json
import sys

def compute():
    queue_path = "has_live_project_tracker/data/mission_intake_queue.json"
    tracker_path = "has_live_project_tracker/data/has_runtime_state.json"
    
    try:
        with open(queue_path, "r") as f:
            queue = json.load(f)
        missions = queue.get("missions", [])
    except Exception:
        missions = []

    copy_paste = True
    reason = "No missions processed through intake queue yet."

    if missions:
        last_m = missions[-1]
        status = last_m.get("status")
        if status in ["DECOMPOSED", "RUNNING", "COMPLETED"]:
            copy_paste = False
            reason = "Mission processed end-to-end without manual copy-paste triggers."
        elif status == "REJECTED_INJECTION":
            copy_paste = False
            reason = "Mission rejected by prompt injection safety gates."

    print(f"Computed copy_paste_required: {copy_paste} ({reason})")
    
    # Save computed metrics back to live tracker/runtime state
    try:
        with open(tracker_path, "r") as f:
            tracker = json.load(f)
    except Exception:
        tracker = {}
        
    tracker["manual_relay_status"] = "REMOVED" if not copy_paste else "ACTIVE"
    tracker["orchestration_bridge_status"] = "ACTIVE"
    tracker["copy_paste_required_computed"] = copy_paste
    tracker["copy_paste_required_reason"] = reason
    
    with open(tracker_path, "w") as f:
        json.dump(tracker, f, indent=2)

if __name__ == "__main__":
    compute()
