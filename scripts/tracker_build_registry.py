#!/usr/bin/env python3
import os
import sys
import json
import sqlite3
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "has_live_project_tracker", "data")

REGISTRY_CANDIDATES_PATH = os.path.join(DATA_DIR, "registry_candidates.json")
GLOBAL_REGISTRY_JSON_PATH = os.path.join(DATA_DIR, "global_project_registry.json")
GLOBAL_REGISTRY_DB_PATH = os.path.join(DATA_DIR, "global_project_registry.sqlite")
REGISTRY_SUMMARY_PATH = os.path.join(DATA_DIR, "registry_summary.json")
MONETIZATION_PATH = os.path.join(DATA_DIR, "monetization_candidates.json")
DEVSECOPS_PATH = os.path.join(DATA_DIR, "devsecops_candidates.json")

def main():
    print("==================================================")
    print("BUILDING GLOBAL PROJECT REGISTRY (T011)")
    print("==================================================")

    if not os.path.exists(REGISTRY_CANDIDATES_PATH):
        print(f"Error: registry_candidates.json not found at {REGISTRY_CANDIDATES_PATH}", file=sys.stderr)
        sys.exit(1)

    with open(REGISTRY_CANDIDATES_PATH, 'r', encoding='utf-8') as f:
        candidates = json.load(f)

    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    
    global_registry = []
    monetization_candidates = []
    devsecops_candidates = []

    # 1. Initialize SQLite connection and schemas
    print(f"Initializing SQLite Registry Database: {GLOBAL_REGISTRY_DB_PATH}...")
    if os.path.exists(GLOBAL_REGISTRY_DB_PATH):
        os.remove(GLOBAL_REGISTRY_DB_PATH) # Start fresh

    conn = sqlite3.connect(GLOBAL_REGISTRY_DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE registry_assets (
        canonical_id TEXT PRIMARY KEY,
        canonical_name TEXT,
        type TEXT,
        domain TEXT,
        paths TEXT,
        remotes TEXT,
        owner_agent TEXT,
        accountable_agent TEXT,
        responsible_agents TEXT,
        evidence_status TEXT,
        qa_status TEXT,
        security_status TEXT,
        monetization_potential TEXT,
        production_readiness TEXT,
        confidence REAL,
        gaps TEXT,
        next_action TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE source_records (
        raw_id TEXT PRIMARY KEY,
        canonical_id TEXT,
        FOREIGN KEY(canonical_id) REFERENCES registry_assets(canonical_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE monetization_candidates (
        canonical_id TEXT PRIMARY KEY,
        canonical_name TEXT,
        domain TEXT,
        type TEXT,
        monetization_potential TEXT,
        owner_agent TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE devsecops_candidates (
        canonical_id TEXT PRIMARY KEY,
        canonical_name TEXT,
        domain TEXT,
        type TEXT,
        security_status TEXT,
        owner_agent TEXT
    )
    """)

    conn.commit()

    # 2. Iterate candidates, apply monetization/DevSecOps heuristics, and insert records
    print("Compiling registry entries and inserting into SQLite tables...")
    for c in candidates:
        name = c["canonical_name"]
        asset_type = c["type"]
        domain = c["domain"]
        owner = c["owner_agent"]

        # Monetization potential heuristics
        potential = "LOW"
        is_monetization = (
            "monetize" in name.lower() or 
            "invest" in name.lower() or 
            "budget" in name.lower() or
            "accel" in name.lower() or
            "stripe" in name.lower() or
            "payment" in name.lower() or
            "billing" in name.lower() or
            "training" in name.lower() or
            "radar" in name.lower() or
            "forge" in name.lower() or
            domain in ["monetization", "business"]
        )
        if is_monetization and asset_type in ["application", "repo", "repository", "service", "script", "document"]:
            potential = "HIGH"

        c["monetization_potential"] = potential

        # DevSecOps scanning heuristics
        is_devsecops = (
            asset_type in ["repo", "repository", "application", "service", "build_config"] or
            "api" in name.lower() or
            "gateway" in name.lower() or
            "backend" in name.lower() or
            "swarm" in name.lower()
        )
        security_status = "VERIFIED"
        if is_devsecops:
            # If evidence is missing or unverified, it's flagged as scan target
            if c.get("evidence_status") != "VERIFIED" or "uncommitted" in str(c.get("gaps", "")):
                security_status = "REQUIRES_SCAN"

        c["security_status"] = security_status

        # Missing README/Test/Security check
        gaps = list(c.get("gaps", []))
        if asset_type in ["repo", "application", "service"]:
            # Check for README files or testing files
            has_readme = any(["readme" in str(p).lower() for p in c.get("paths", []) + c.get("remotes", [])])
            if not has_readme:
                gaps.append("Missing README documentation file")
            
            # Check if there are any associated E2E or unit tests
            has_tests = any(["test" in str(p).lower() or "spec" in str(p).lower() for p in c.get("paths", [])])
            if not has_tests:
                gaps.append("Missing automated unit or integration tests")

        c["gaps"] = gaps

        # Append to master arrays
        global_registry.append(c)

        if potential == "HIGH":
            monetization_candidates.append({
                "canonical_id": c["canonical_id"],
                "canonical_name": name,
                "domain": domain,
                "type": asset_type,
                "monetization_potential": potential,
                "owner_agent": owner
            })

        if security_status == "REQUIRES_SCAN":
            devsecops_candidates.append({
                "canonical_id": c["canonical_id"],
                "canonical_name": name,
                "domain": domain,
                "type": asset_type,
                "security_status": security_status,
                "owner_agent": owner
            })

        # Insert into sqlite registry_assets
        cursor.execute("""
        INSERT INTO registry_assets (
            canonical_id, canonical_name, type, domain, paths, remotes,
            owner_agent, accountable_agent, responsible_agents,
            evidence_status, qa_status, security_status,
            monetization_potential, production_readiness, confidence, gaps, next_action
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            c["canonical_id"],
            name,
            asset_type,
            domain,
            json.dumps(c.get("paths", [])),
            json.dumps(c.get("remotes", [])),
            owner,
            c.get("accountable_agent", owner),
            json.dumps(c.get("responsible_agents", [owner])),
            c.get("evidence_status", "VERIFIED"),
            c.get("qa_status", "UNKNOWN"),
            security_status,
            potential,
            c.get("production_readiness", "GO"),
            c.get("confidence", 1.0),
            json.dumps(gaps),
            c.get("next_action", "canonicalize")
        ))

        # Insert source records mapping
        for raw_id in c.get("source_records", []):
            cursor.execute("INSERT OR REPLACE INTO source_records (raw_id, canonical_id) VALUES (?, ?)", (raw_id, c["canonical_id"]))

    # Insert monetization and DevSecOps candidates into their specific tables
    for mc in monetization_candidates:
        cursor.execute("INSERT INTO monetization_candidates VALUES (?, ?, ?, ?, ?, ?)", (
            mc["canonical_id"], mc["canonical_name"], mc["domain"], mc["type"], mc["monetization_potential"], mc["owner_agent"]
        ))

    for dc in devsecops_candidates:
        cursor.execute("INSERT INTO devsecops_candidates VALUES (?, ?, ?, ?, ?, ?)", (
            dc["canonical_id"], dc["canonical_name"], dc["domain"], dc["type"], dc["security_status"], dc["owner_agent"]
        ))

    conn.commit()
    conn.close()

    # 3. Save JSON Outputs
    with open(GLOBAL_REGISTRY_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(global_registry, f, indent=2)

    with open(MONETIZATION_PATH, 'w', encoding='utf-8') as f:
        json.dump(monetization_candidates, f, indent=2)

    with open(DEVSECOPS_PATH, 'w', encoding='utf-8') as f:
        json.dump(devsecops_candidates, f, indent=2)

    # 4. Save registry_summary.json
    total_gaps = sum([len(c["gaps"]) for c in global_registry])
    summary = {
        "canonical_project_count": len(global_registry),
        "monetization_candidates_count": len(monetization_candidates),
        "devsecops_candidates_count": len(devsecops_candidates),
        "total_gaps_count": total_gaps,
        "last_updated": timestamp
    }

    with open(REGISTRY_SUMMARY_PATH, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    print("Master Project Registry outputs successfully compiled:")
    print(f" • Canonical Projects:       {len(global_registry)}")
    print(f" • Monetization Candidates:   {len(monetization_candidates)}")
    print(f" • DevSecOps Targets:         {len(devsecops_candidates)}")
    print(f" • Uncovered Registry Gaps:  {total_gaps}")

if __name__ == "__main__":
    main()
