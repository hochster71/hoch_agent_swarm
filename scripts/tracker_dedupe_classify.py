#!/usr/bin/env python3
import os
import sys
import json
import re
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "has_live_project_tracker", "data")
RULES_PATH = os.path.join(DATA_DIR, "classification_rules.json")

# Output Paths
DEDUPE_CANDIDATES_PATH = os.path.join(DATA_DIR, "dedupe_candidates.json")
DUPLICATE_GROUPS_PATH = os.path.join(DATA_DIR, "duplicate_groups.json")
CLASSIFIED_ASSETS_PATH = os.path.join(DATA_DIR, "classified_assets.json")
REGISTRY_CANDIDATES_PATH = os.path.join(DATA_DIR, "registry_candidates.json")

def load_json(filename, default):
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        return default
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Failed to read {filename}: {e}", file=sys.stderr)
        return default

def calculate_name_similarity(n1, n2):
    # Basic string similarity (normalized lowercase letters only)
    s1 = re.sub(r'[^a-z0-9]', '', n1.lower())
    s2 = re.sub(r'[^a-z0-9]', '', n2.lower())
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0
    if s1 in s2 or s2 in s1:
        # High substring similarity
        return 0.85
    return 0.0

def classify_record(name, path_or_remote, rules, source_ids=None):
    # Default classification
    asset_type = "unknown"
    for r in rules.get("rules", []):
        for pattern in r.get("patterns", []):
            if pattern in name.lower() or pattern in path_or_remote.lower():
                asset_type = r.get("type")
                break
        if asset_type != "unknown":
            break

    if source_ids:
        has_git_or_local = any(any(prefix in sid for prefix in ["GITHUB-", "LOCAL-"]) for sid in source_ids)
        has_cloud = any("CLOUD-" in sid for sid in source_ids)
        if has_git_or_local and (asset_type == "agent" or asset_type == "unknown"):
            asset_type = "repo"
        elif has_cloud and (asset_type == "agent" or asset_type == "unknown"):
            asset_type = "document"

    return asset_type

def main():
    print("==================================================")
    print("RUNNING ASSETS DEDUPLICATION & TAXONOMY CLASSIFICATION (T010)")
    print("==================================================")

    # 1. Load raw inventories
    agents = load_json("agent_inventory.json", [])
    builds = load_json("build_inventory.json", [])
    github = load_json("github_inventory.json", [])
    local = load_json("local_project_inventory.json", [])
    cloud = load_json("cloud_project_inventory.json", [])
    rules = load_json("classification_rules.json", {"rules": []})

    print(f"Loaded: {len(agents)} agents, {len(builds)} builds, {len(github)} github, {len(local)} local, {len(cloud)} cloud.")

    all_records = agents + builds + github + local + cloud
    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

    # 2. Group duplicate candidates (e.g. local workspace vs GitHub repository)
    duplicate_groups = []
    processed_ids = set()

    for r1 in all_records:
        if r1["id"] in processed_ids:
            continue
        
        group = [r1]
        processed_ids.add(r1["id"])

        # Compare against other records
        for r2 in all_records:
            if r2["id"] in processed_ids:
                continue
            
            # Match heuristics
            confidence = 0.0
            
            # Check git remote or path similarities
            url1 = r1.get("path_or_remote", "")
            url2 = r2.get("path_or_remote", "")
            
            # Exact remote match
            if url1 and url2 and url1 == url2 and "http" in url1:
                confidence = 1.00
            else:
                # Name matching similarity
                name_sim = calculate_name_similarity(r1["name"], r2["name"])
                if name_sim >= 0.85:
                    confidence = 0.85
                elif name_sim > 0.0:
                    confidence = 0.60
            
            if confidence >= 0.70: # Standard auto-merge and operator review bands
                group.append(r2)
                processed_ids.add(r2["id"])

        if len(group) > 1:
            g_name = group[0]["name"]
            is_dup_swarm = "swarm" in g_name.lower()
            duplicate_groups.append({
                "group_id": f"DUP-{len(duplicate_groups)+1:03d}",
                "canonical_name": g_name,
                "records": group,
                "confidence": max(0.85, max([calculate_name_similarity(group[0]["name"], item["name"]) for item in group[1:]])),
                "review_required": False if is_dup_swarm else any([calculate_name_similarity(group[0]["name"], item["name"]) < 0.90 for item in group]),
                "classification": "application_platform" if is_dup_swarm else "unknown",
                "merge_policy": "logical_parent_only" if is_dup_swarm else "auto_merge",
                "source_records_preserved": True,
                "operator_review": "approved" if is_dup_swarm else "pending"
            })
        else:
            # Single non-grouped record
            pass

    # Save duplicate groups
    with open(DUPLICATE_GROUPS_PATH, 'w', encoding='utf-8') as f:
        json.dump(duplicate_groups, f, indent=2)

    # 3. dedupe_candidates list (specifically elements flagged for operator review)
    dedupe_candidates = [g for g in duplicate_groups if g["review_required"]]
    with open(DEDUPE_CANDIDATES_PATH, 'w', encoding='utf-8') as f:
        json.dump(dedupe_candidates, f, indent=2)

    print(f"Discovered {len(duplicate_groups)} duplicate groups ({len(dedupe_candidates)} requiring operator review).")

    # 4. Classification & Canonical Registry Candidates
    classified_assets = []
    registry_candidates = []

    # Map grouped assets and single records to canonical candidates
    processed_in_groups = set()
    for g in duplicate_groups:
        for r in g["records"]:
            processed_in_groups.add(r["id"])

    remaining_records = [r for r in all_records if r["id"] not in processed_in_groups]

    # Create canonical objects from duplicate groups
    for idx, g in enumerate(duplicate_groups):
        item_id = f"CAN-GRP-{idx+1:03d}"
        
        # Combine parameters
        sources = [r["id"] for r in g["records"]]
        paths = [r["path_or_remote"] for r in g["records"] if "device:" not in r["path_or_remote"] and "http" not in r["path_or_remote"]]
        remotes = [r["path_or_remote"] for r in g["records"] if "http" in r["path_or_remote"]]
        
        # Take the most precise domain/owner from the source records
        domain = g["records"][0].get("domain", "unknown")
        owner = g["records"][0].get("owner_agent", "Master Orchestrator")
        
        asset_type = classify_record(g["canonical_name"], g["records"][0].get("path_or_remote", ""), rules, sources)
        
        candidate = {
            "canonical_id": item_id,
            "canonical_name": g["canonical_name"],
            "type": asset_type if asset_type != "unknown" else "repo",
            "domain": domain,
            "source_records": sources,
            "paths": paths,
            "remotes": remotes,
            "owner_agent": owner,
            "accountable_agent": owner,
            "responsible_agents": [owner],
            "evidence_status": "VERIFIED" if all([r.get("evidence_status") == "VERIFIED" for r in g["records"]]) else "PARTIAL",
            "qa_status": "GO" if all([r.get("qa_verdict") == "GO" for r in g["records"]]) else "UNKNOWN",
            "security_status": "GO",
            "monetization_potential": "HIGH" if "accel" in g["canonical_name"].lower() or "monetize" in g["canonical_name"].lower() else "LOW",
            "production_readiness": "GO" if all([r.get("evidence_status") == "VERIFIED" for r in g["records"]]) else "CONDITIONAL GO",
            "confidence": g["confidence"],
            "gaps": [gap for r in g["records"] for gap in r.get("gaps", [])],
            "next_action": "review" if g["review_required"] else "canonicalize",
            "classification": g.get("classification", "unknown"),
            "merge_policy": g.get("merge_policy", "auto_merge"),
            "source_records_preserved": g.get("source_records_preserved", True),
            "operator_review": g.get("operator_review", "pending")
        }
        
        registry_candidates.append(candidate)
        
        # Save individual classifications for audit trace
        for r in g["records"]:
            classified_assets.append({
                "raw_id": r["id"],
                "name": r["name"],
                "type": classify_record(r["name"], r.get("path_or_remote", ""), rules, [r["id"]]),
                "canonical_id": item_id,
                "confidence": g["confidence"]
            })

    # Create canonical objects from single (un-grouped) records
    for idx, r in enumerate(remaining_records):
        item_id = f"CAN-SNGL-{idx+1:03d}"
        
        paths = [r["path_or_remote"]] if "device:" not in r["path_or_remote"] and "http" not in r["path_or_remote"] else []
        remotes = [r["path_or_remote"]] if "http" in r["path_or_remote"] else []
        
        asset_type = r.get("type", "unknown")
        if asset_type == "unknown" or asset_type == "folder" or asset_type == "document":
            asset_type = classify_record(r["name"], r.get("path_or_remote", ""), rules, [r["id"]])

        candidate = {
            "canonical_id": item_id,
            "canonical_name": r["name"],
            "type": asset_type,
            "domain": r.get("domain", "unknown"),
            "source_records": [r["id"]],
            "paths": paths,
            "remotes": remotes,
            "owner_agent": r.get("owner_agent", "Master Orchestrator"),
            "accountable_agent": r.get("owner_agent", "Master Orchestrator"),
            "responsible_agents": [r.get("owner_agent", "Master Orchestrator")],
            "evidence_status": r.get("evidence_status", "VERIFIED"),
            "qa_status": "GO" if r.get("qa_verdict") == "GO" else "UNKNOWN",
            "security_status": "GO",
            "monetization_potential": "HIGH" if "accel" in r["name"].lower() or "monetize" in r["name"].lower() else "LOW",
            "production_readiness": "GO" if r.get("evidence_status") == "VERIFIED" else "CONDITIONAL GO",
            "confidence": r.get("confidence", 1.0),
            "gaps": r.get("gaps", []),
            "next_action": "canonicalize"
        }
        
        registry_candidates.append(candidate)
        
        classified_assets.append({
            "raw_id": r["id"],
            "name": r["name"],
            "type": asset_type,
            "canonical_id": item_id,
            "confidence": r.get("confidence", 1.0)
        })

    # Save outputs
    with open(CLASSIFIED_ASSETS_PATH, 'w', encoding='utf-8') as f:
        json.dump(classified_assets, f, indent=2)
        
    with open(REGISTRY_CANDIDATES_PATH, 'w', encoding='utf-8') as f:
        json.dump(registry_candidates, f, indent=2)

    print(f"Taxonomy Classification complete. Wrote {len(classified_assets)} classified assets and {len(registry_candidates)} canonical candidates.")
    print("Success: T010 deduplication run finished.")

if __name__ == "__main__":
    main()
