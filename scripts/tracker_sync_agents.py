#!/usr/bin/env python3
import os
import sys
import json
import urllib.request
from datetime import datetime

STATUS_URL = "http://127.0.0.1:8000/api/v1/agents/status"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATUS_JSON_PATH = os.path.join(SCRIPT_DIR, "..", "has_live_project_tracker", "data", "status.json")

def fetch_live_statuses():
    try:
        req = urllib.request.Request(STATUS_URL)
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Warning: Failed to fetch live agent status from {STATUS_URL}: {e}", file=sys.stderr)
        return None

def main():
    print("==================================================")
    print("SYNCING HAS AGENT STATUS FEED (T005)")
    print("==================================================")

    if not os.path.exists(STATUS_JSON_PATH):
        print(f"Error: status.json not found at {STATUS_JSON_PATH}", file=sys.stderr)
        sys.exit(1)

    with open(STATUS_JSON_PATH, 'r', encoding='utf-8') as f:
        status_data = json.load(f)

    live_data = fetch_live_statuses()
    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

    # Mapping of tracker agents to live devices or specific nodes
    # If live_data is available, we set tracker agent statuses dynamically
    devices = {}
    if live_data and "data" in live_data and "devices" in live_data["data"]:
        for dev in live_data["data"]["devices"]:
            devices[dev["id"]] = dev["status"]

    print("Mapping tracker agent statuses...")
    for agent in status_data.get("agents", []):
        name = agent["name"]
        old_status = agent.get("status", "Queued")
        
        # Simple mapping heuristic
        if name == "Master Orchestrator":
            new_status = devices.get("L1", "Running")
        elif name == "QA Auditor Agent":
            new_status = devices.get("L1", "Running")  # Running on Master L1
        elif name == "Security Auditor Agent":
            new_status = devices.get("W1", "Running")  # Running on Coder W1
        elif name == "HASF Pipeline Agent":
            new_status = devices.get("L3", "Running")  # Running on Deployer L3
        elif name == "Evidence Collector Agent":
            new_status = devices.get("L2", "Running")  # Running on Coder L2
        elif name == "Live Tracker Runtime Agent":
            new_status = "Running"                      # Always running (this app)
        elif name == "Production Acceleration Agent":
            new_status = "Running"                      # Running the CP engine
        elif name == "Data Consolidation Agent":
            new_status = "Running"                      # Active for Batch A
        else:
            # Personal, Business, Research agents
            new_status = devices.get("L1", "Running")

        # Map state string from API (e.g. Active/Triaging/Deploying -> Running)
        if new_status in ["Active", "Triaging", "Deploying", "Self-Healing"]:
            new_status = "Running"
        elif new_status in ["Inactive", "Offline"]:
            new_status = "Queued"

        agent["status"] = new_status
        agent["last_update"] = timestamp
        print(f" • {name}: {old_status} -> {new_status}")

    with open(STATUS_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(status_data, f, indent=2)

    print("Success: Agent statuses updated in status.json.")

if __name__ == "__main__":
    main()
