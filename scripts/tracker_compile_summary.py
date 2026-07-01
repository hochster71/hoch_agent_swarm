#!/usr/bin/env python3
import os
import sys
import json
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "has_live_project_tracker", "data")

SUMMARY_PATH = os.path.join(DATA_DIR, "inventory_summary.json")

def load_count_and_status(filename):
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        return 0, "MISSING", []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            # Extract any gaps/blockers from items
            blockers = []
            for item in data:
                for gap in item.get("gaps", []):
                    if gap not in blockers:
                        blockers.append(gap)
            
            status = "VERIFIED"
            for item in data:
                if item.get("evidence_status") == "PARTIAL":
                    status = "PARTIAL"
                    break
            
            return len(data), status, blockers
    except Exception as e:
        print(f"Error reading {filename}: {e}", file=sys.stderr)
        return 0, "ERROR", []

def main():
    print("==================================================")
    print("COMPILING INVENTORY SUMMARY (T011 / Summary)")
    print("==================================================")

    agent_count, agent_status, _ = load_count_and_status("agent_inventory.json")
    build_count, build_status, _ = load_count_and_status("build_inventory.json")
    github_count, github_status, _ = load_count_and_status("github_inventory.json")
    local_count, local_status, local_blockers = load_count_and_status("local_project_inventory.json")
    cloud_count, cloud_status, cloud_blockers = load_count_and_status("cloud_project_inventory.json")

    total_items = agent_count + build_count + github_count + local_count + cloud_count

    # Aggregate all blockers/gaps
    all_blockers = local_blockers + cloud_blockers

    # Overall verdict
    overall_status = "VERIFIED"
    if cloud_status == "PARTIAL" or github_status == "PARTIAL" or local_status == "PARTIAL":
        overall_status = "PARTIAL"

    summary = {
        "agent_count": agent_count,
        "agent_status": agent_status,
        "build_count": build_count,
        "build_status": build_status,
        "github_count": github_count,
        "github_status": github_status,
        "local_count": local_count,
        "local_status": local_status,
        "cloud_count": cloud_count,
        "cloud_status": cloud_status,
        "total_items": total_items,
        "overall_status": overall_status,
        "blockers": all_blockers,
        "last_updated": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    }

    with open(SUMMARY_PATH, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    print(f"Summary compiled successfully at {SUMMARY_PATH}:")
    print(f" • Total Items: {total_items}")
    print(f" • Status:      {overall_status}")
    if all_blockers:
        print(f" • Partials/Blockers: {all_blockers}")

if __name__ == "__main__":
    main()
