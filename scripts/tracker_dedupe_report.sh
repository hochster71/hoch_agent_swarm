#!/usr/bin/env python3
import os
import sys
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "has_live_project_tracker", "data")

DUPLICATE_GROUPS_PATH = os.path.join(DATA_DIR, "duplicate_groups.json")
DEDUPE_CANDIDATES_PATH = os.path.join(DATA_DIR, "dedupe_candidates.json")
CLASSIFIED_ASSETS_PATH = os.path.join(DATA_DIR, "classified_assets.json")

def main():
    print("==================================================")
    print("HAS/HASF DEDUPLICATION & CLASSIFICATION REPORT")
    print("==================================================")

    if not os.path.exists(DUPLICATE_GROUPS_PATH):
        print("Error: duplicate_groups.json not found.", file=sys.stderr)
        sys.exit(1)

    with open(DUPLICATE_GROUPS_PATH, 'r', encoding='utf-8') as f:
        groups = json.load(f)

    with open(DEDUPE_CANDIDATES_PATH, 'r', encoding='utf-8') as f:
        candidates = json.load(f)

    with open(CLASSIFIED_ASSETS_PATH, 'r', encoding='utf-8') as f:
        classified = json.load(f)

    print(f"Total Discovered Duplicate Groups: {len(groups)}")
    print(f"Groups Requiring Operator Review:  {len(candidates)}")
    print(f"Total Classified Raw Assets:      {len(classified)}")
    print("--------------------------------------------------")

    if candidates:
        print("REVIEW REQUIRED MERGES:")
        for c in candidates:
            print(f" • Group: {c['canonical_name']} (ID: {c['group_id']}) - Confidence: {c['confidence']:.2f}")
            for r in c['records']:
                print(f"    - Raw ID: {r['id']} | Source: {r['source']} | Path: {r.get('path_or_remote')}")
    else:
        print("No merges requiring immediate review.")

    print("--------------------------------------------------")
    unknowns = [a for a in classified if a["type"] == "unknown"]
    print(f"Raw Assets with 'unknown' Classification: {len(unknowns)}")
    for u in unknowns[:10]:
        print(f" • Raw ID: {u['raw_id']} | Name: {u['name']}")
    if len(unknowns) > 10:
        print(f"   ... and {len(unknowns)-10} more.")

if __name__ == "__main__":
    main()
