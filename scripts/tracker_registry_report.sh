#!/usr/bin/env python3
import os
import sys
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "has_live_project_tracker", "data")

GLOBAL_REGISTRY_JSON_PATH = os.path.join(DATA_DIR, "global_project_registry.json")
MONETIZATION_PATH = os.path.join(DATA_DIR, "monetization_candidates.json")
DEVSECOPS_PATH = os.path.join(DATA_DIR, "devsecops_candidates.json")
REGISTRY_SUMMARY_PATH = os.path.join(DATA_DIR, "registry_summary.json")

def main():
    print("==================================================")
    print("HAS/HASF GLOBAL PROJECT REGISTRY REPORT")
    print("==================================================")

    if not os.path.exists(GLOBAL_REGISTRY_JSON_PATH):
        print("Error: global_project_registry.json not found.", file=sys.stderr)
        sys.exit(1)

    with open(GLOBAL_REGISTRY_JSON_PATH, 'r', encoding='utf-8') as f:
        registry = json.load(f)

    with open(MONETIZATION_PATH, 'r', encoding='utf-8') as f:
        monetization = json.load(f)

    with open(DEVSECOPS_PATH, 'r', encoding='utf-8') as f:
        devsecops = json.load(f)

    with open(REGISTRY_SUMMARY_PATH, 'r', encoding='utf-8') as f:
        summary = json.load(f)

    print(f"Canonical Registry Count:      {summary['canonical_project_count']}")
    print(f"Monetization Candidates Count: {summary['monetization_candidates_count']}")
    print(f"DevSecOps Scan Targets Count:  {summary['devsecops_candidates_count']}")
    print(f"Total Discovered Gaps Count:   {summary['total_gaps_count']}")
    print(f"Last Registry Compilation:    {summary['last_updated']}")
    print("--------------------------------------------------")

    print("MONETIZATION CANDIDATES (HIGH POTENTIAL):")
    for m in monetization[:10]:
        print(f" • Project: {m['canonical_name']} (ID: {m['canonical_id']}) | Type: {m['type']} | Domain: {m['domain']}")
    if len(monetization) > 10:
        print(f"   ... and {len(monetization)-10} more.")

    print("--------------------------------------------------")
    print("DEVSECOPS SCAN TARGETS (REQUIRES SCAN):")
    for d in devsecops[:10]:
        print(f" • Project: {d['canonical_name']} (ID: {d['canonical_id']}) | Type: {d['type']} | Domain: {d['domain']}")
    if len(devsecops) > 10:
        print(f"   ... and {len(devsecops)-10} more.")

    print("--------------------------------------------------")
    print("TOP CANONICAL ASSET GAPS:")
    gaps_found = 0
    for c in registry:
        if c.get("gaps"):
            print(f" • Project: {c['canonical_name']} (ID: {c['canonical_id']})")
            for gap in c["gaps"]:
                print(f"    - {gap}")
            gaps_found += 1
            if gaps_found >= 5:
                break
    if not gaps_found:
        print("No gaps found in any canonical assets.")

if __name__ == "__main__":
    main()
