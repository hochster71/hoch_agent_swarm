#!/usr/bin/env python3
import os
import sys
import json
import urllib.request
import urllib.error
import base64

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TASKS_PATH = os.path.join(SCRIPT_DIR, "..", "has_live_project_tracker", "data", "tasks.json")
SECRETS_PATH = os.path.join(os.path.expanduser("~"), ".hoch-secrets", "has-tracker.env")

# 1. Read tasks.json
if not os.path.exists(TASKS_PATH):
    print("NO DATA: tasks.json not found")
    sys.exit(0)

try:
    with open(TASKS_PATH, "r", encoding="utf-8") as f:
        tasks = json.load(f)
except Exception as e:
    print(f"NO DATA: Failed to parse tasks.json: {e}")
    sys.exit(0)

# Filter tasks that have evidence files
tasks_with_evidence = [t for t in tasks if t.get("evidence") and t.get("status") == "Done"]
if not tasks_with_evidence:
    print("NO DATA: No completed tasks with evidence found")
    sys.exit(0)

# Limit to top/recent 5 tasks to prevent spamming
tasks_to_emit = tasks_with_evidence[:5]

# 2. Load secrets/credentials
user = "admin"
password = "change-this-password"
port = "3001"

if os.path.exists(SECRETS_PATH):
    try:
        with open(SECRETS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip()
                if k == "TRACKER_USER":
                    user = v
                elif k == "TRACKER_PASSWORD":
                    password = v
                elif k == "TRACKER_PORT":
                    port = v
    except Exception as e:
        print(f"Warning: Failed to load secrets: {e}", file=sys.stderr)

url = f"http://localhost:{port}/api/event"

# 3. Emit evidence events
success_count = 0
for task in tasks_to_emit:
    tid = task.get("id")
    name = task.get("name", "Unknown Task")
    evidence_list = task.get("evidence", [])
    evidence_path = evidence_list[0] if evidence_list else None
    
    # Construct evidence event
    event = {
        "type": "evidence_event",
        "source": "qa_gate",
        "target": "evidence_vault",
        "domain": "Evidence",
        "severity": "success",
        "status": "success",
        "payload_summary": f"Evidence submitted for task {tid}: {os.path.basename(evidence_path)}",
        "evidence_path": evidence_path
    }
    
    # Post event
    req = urllib.request.Request(url, data=json.dumps(event).encode("utf-8"), headers={
        "Content-Type": "application/json"
    })
    auth_str = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("utf-8")
    req.add_header("Authorization", f"Basic {auth_str}")
    
    try:
        with urllib.request.urlopen(req) as resp:
            if resp.status == 200:
                success_count += 1
    except urllib.error.URLError as e:
        print(f"Error posting evidence event for {tid}: {e}", file=sys.stderr)

print(f"Emitted {success_count} evidence events to the Control Plane stream.")
