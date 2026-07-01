#!/usr/bin/env python3
import os
import sys
import json
import urllib.request
import urllib.error
import base64

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATUS_PATH = os.path.join(SCRIPT_DIR, "..", "has_live_project_tracker", "data", "status.json")
SECRETS_PATH = os.path.join(os.path.expanduser("~"), ".hoch-secrets", "has-tracker.env")

# 1. Read status.json
if not os.path.exists(STATUS_PATH):
    print("NO DATA: status.json not found")
    sys.exit(0)

try:
    with open(STATUS_PATH, "r", encoding="utf-8") as f:
        status_data = json.load(f)
except Exception as e:
    print(f"NO DATA: Failed to parse status.json: {e}")
    sys.exit(0)

builds = status_data.get("builds", [])
if not builds:
    print("NO DATA: No builds found in status.json")
    sys.exit(0)

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

# 3. Emit build events
success_count = 0
for build in builds:
    name = build.get("name", "Unknown Build")
    state = build.get("status", "Unknown")
    exit_code = build.get("exit_code", 0)
    command = build.get("command", "")
    evidence = build.get("evidence", [])
    evidence_path = evidence[0] if evidence else None
    
    # Construct build event
    event = {
        "type": "build_event",
        "source": "agent_swarm",
        "target": "build_factory",
        "domain": "Build",
        "severity": "success" if exit_code == 0 else "error",
        "status": "success" if state.lower() == "done" else "failed",
        "payload_summary": f"Build {name}: {command} finished with exit code {exit_code}",
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
        print(f"Error posting build event for {name}: {e}", file=sys.stderr)

print(f"Emitted {success_count} build events to the Control Plane stream.")
