#!/usr/bin/env python3
import os
import sys
import json

def verify_intake_security():
    queue_path = "has_live_project_tracker/data/mission_intake_queue.json"
    
    # Check permissions (on Unix systems)
    if os.name == "posix":
        mode = os.stat(queue_path).st_mode
        if mode & 0o002:
            print("❌ Verification failed: mission_intake_queue.json is world-writable.")
            sys.exit(1)

    try:
        with open(queue_path, "r") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        sys.exit(1)

    missions = data.get("missions", [])
    for mission in missions:
        sig_status = mission.get("signature_status")
        # Rejected unsigned
        if sig_status == "UNSIGNED" and mission.get("status") not in ["REJECTED_UNSIGNED", "BLOCKED"]:
            print(f"❌ Verification failed: Unsigned mission {mission.get('mission_id')} processed.")
            sys.exit(1)
            
        # Injection check
        if mission.get("sanitization_status") == "FAIL" and mission.get("status") != "REJECTED_INJECTION":
            print(f"❌ Verification failed: Injection mission {mission.get('mission_id')} not blocked.")
            sys.exit(1)

    print("🟢 Mission intake security verification PASSED.")
    return True

if __name__ == "__main__":
    verify_intake_security()
