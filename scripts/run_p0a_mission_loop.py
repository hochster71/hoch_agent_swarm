#!/usr/bin/env python3
import urllib.request
import json
import uuid
import sys
import os

def run_loop():
    print("==================================================")
    print("P0a: Executing Mission Control E2E Loop")
    print("==================================================")
    
    mission_id = f"mission-p0a-fury-{uuid.uuid4().hex[:8]}"
    print(f"Generated Mission ID: {mission_id}")
    
    # 1. Post to intake
    intake_url = "http://127.0.0.1:8000/api/v1/pods/mission/intake"
    payload = {
        "mission_id": mission_id,
        "name": "E2E P0a Loop Validation Run",
        "target_pod": "business",
        "command": "LAUNCH",
        "parameters": {}
    }
    
    req_data = json.dumps(payload).encode("utf-8")
    
    print("\n1. Submitting mission intake request...")
    try:
        req = urllib.request.Request(intake_url, data=req_data, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req) as resp:
            res_body = json.loads(resp.read().decode("utf-8"))
            print(f"Intake Response: {json.dumps(res_body, indent=2)}")
    except Exception as e:
        print(f"❌ Intake request failed: {e}")
        sys.exit(1)
        
    # 2. Check status
    print("\n2. Checking mission status in DB...")
    status_url = "http://127.0.0.1:8000/api/v1/pods/missions"
    try:
        with urllib.request.urlopen(status_url) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            mission = None
            for m in data.get("missions", []):
                if m["mission_id"] == mission_id:
                    mission = m
                    break
            if not mission:
                print("❌ Mission not found in database!")
                sys.exit(1)
            print(f"Mission found in DB: ID={mission['mission_id']}, Status={mission['status']}")
            if mission["status"] != "WAITING_FOR_APPROVAL":
                print(f"❌ Unexpected status: {mission['status']}, expected WAITING_FOR_APPROVAL")
                sys.exit(1)
    except Exception as e:
        print(f"❌ Status check failed: {e}")
        sys.exit(1)
        
    # 3. Post approval
    print("\n3. Posting founder/operator approval...")
    approve_url = f"http://127.0.0.1:8000/api/v1/pods/missions/{mission_id}/approve"
    try:
        req = urllib.request.Request(approve_url, data=b"", method="POST")
        with urllib.request.urlopen(req) as resp:
            res_body = json.loads(resp.read().decode("utf-8"))
            print(f"Approval Response: {json.dumps(res_body, indent=2)}")
    except Exception as e:
        print(f"❌ Approval failed: {e}")
        sys.exit(1)
        
    # 4. Verify completed state
    print("\n4. Verifying completed status in DB...")
    try:
        with urllib.request.urlopen(status_url) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            mission = None
            for m in data.get("missions", []):
                if m["mission_id"] == mission_id:
                    mission = m
                    break
            print(f"Final Mission Status: {mission['status']}")
            if mission["status"] != "COMPLETED":
                print("❌ Mission failed to transition to COMPLETED!")
                sys.exit(1)
            print("🟢 E2E loop validation check: SUCCESS.")
    except Exception as e:
        print(f"❌ Final verification failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_loop()
