#!/usr/bin/env python3
import os
import sys
import json
import urllib.request
import urllib.error
import base64

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DORA_PATH = os.path.join(SCRIPT_DIR, "..", "has_live_project_tracker", "data", "dora_events.ndjson")
SECRETS_PATH = os.path.join(os.path.expanduser("~"), ".hoch-secrets", "has-tracker.env")

# 1. Read dora_events.ndjson
if not os.path.exists(DORA_PATH):
    print("NO DATA: dora_events.ndjson not found")
    sys.exit(0)

events = []
try:
    with open(DORA_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.parse(line))
            except:
                try:
                    events.append(json.loads(line))
                except Exception as e:
                    print(f"Warning: Failed to parse DORA event line: {e}", file=sys.stderr)
except Exception as e:
    print(f"NO DATA: Failed to read dora_events.ndjson: {e}")
    sys.exit(0)

if not events:
    print("NO DATA: dora_events.ndjson is empty")
    sys.exit(0)

# Limit to top/recent 5 events
events_to_emit = events[-5:]

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

# 3. Emit DORA events
success_count = 0
for event in events_to_emit:
    change_id = event.get("change_id", "Unknown Change")
    commit = event.get("commit_sha", "Unknown Commit")
    status_val = event.get("deploy_status", "success")
    
    # Construct DORA event
    event_payload = {
        "type": "dora_event",
        "source": "github",
        "target": "qa_gate",
        "domain": "DORA",
        "severity": "success" if status_val == "success" else "error",
        "status": "success" if status_val == "success" else "failed",
        "payload_summary": f"DORA deployment: {change_id} ({commit}) status: {status_val}",
        "evidence_path": None
    }
    
    # Post event
    req = urllib.request.Request(url, data=json.dumps(event_payload).encode("utf-8"), headers={
        "Content-Type": "application/json"
    })
    auth_str = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("utf-8")
    req.add_header("Authorization", f"Basic {auth_str}")
    
    try:
        with urllib.request.urlopen(req) as resp:
            if resp.status == 200:
                success_count += 1
    except urllib.error.URLError as e:
        print(f"Error posting DORA event for {change_id}: {e}", file=sys.stderr)

print(f"Emitted {success_count} DORA events to the Control Plane stream.")
