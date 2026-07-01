#!/usr/bin/env python3
import os
import sys
import json
import urllib.request
import urllib.error
import base64

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REGISTRY_PATH = os.path.join(SCRIPT_DIR, "..", "has_live_project_tracker", "data", "global_project_registry.json")
SECRETS_PATH = os.path.join(os.path.expanduser("~"), ".hoch-secrets", "has-tracker.env")

# 1. Read global_project_registry.json
if not os.path.exists(REGISTRY_PATH):
    print("NO DATA: global_project_registry.json not found")
    sys.exit(0)

try:
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        registry_data = json.load(f)
except Exception as e:
    print(f"NO DATA: Failed to parse global_project_registry.json: {e}")
    sys.exit(0)

if not registry_data:
    print("NO DATA: Global registry is empty")
    sys.exit(0)

# Filter high-interest registry items (monetization candidates or those with gaps)
high_interest = [p for p in registry_data if p.get("monetization_potential") == "HIGH" or p.get("gaps")]
if not high_interest:
    # Fallback to first 3 items
    high_interest = registry_data[:3]

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

# 3. Emit registry events
success_count = 0
for project in high_interest:
    name = project.get("canonical_name", "Unknown Project")
    proj_type = project.get("type", "Unknown")
    domain = project.get("domain", "Unknown")
    
    # Construct registry event
    event = {
        "type": "registry_event",
        "source": "local_disk",
        "target": "global_registry",
        "domain": "Registry",
        "severity": "info",
        "status": "success",
        "payload_summary": f"Registry indexed project: {name} ({proj_type}) under domain {domain}",
        "evidence_path": None
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
        print(f"Error posting registry event for {name}: {e}", file=sys.stderr)

print(f"Emitted {success_count} registry events to the Control Plane stream.")
