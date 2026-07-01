#!/usr/bin/env python3
# scripts/generate_revenue_action_queue.py
# Compiles project blockers and evidence gaps into a prioritized, ranked action queue.

import os
import json
import re
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY_PATH = os.path.join(PROJECT_ROOT, "has_live_project_tracker/data/project_inventory.json")
RESULTS_PATH = os.path.join(PROJECT_ROOT, "has_live_project_tracker/data/project_revenue_readiness_results.json")
QUEUE_PATH = os.path.join(PROJECT_ROOT, "has_live_project_tracker/data/revenue_action_queue.json")
REPORT_PATH = os.path.join(PROJECT_ROOT, "docs/evidence/business/revenue-action-queue.md")

# Blocker metadata mappings for impact, ordering and recommended agents
BLOCKER_MAPPING = {
    "No direct project directory or repository available in primary builds": {
        "title": "Resolve Missing Primary Repository Directory",
        "description": "Establish the project repository directory and link it into primary builds for HASF discovery.",
        "revenue_impact": 50,
        "security_impact": 0,
        "deployment_impact": 50,
        "recommended_agent": "Lead Swarm Orchestrator",
        "dependency_order": 1
    },
    "Project repository path does not exist on disk": {
        "title": "Link Project Path to Local Disk",
        "description": "Configure the local file path for project repository assets to enable code inspection.",
        "revenue_impact": 10,
        "security_impact": 0,
        "deployment_impact": 40,
        "recommended_agent": "Lead Swarm Orchestrator",
        "dependency_order": 1
    },
    "Stripe integration code is missing or unverified": {
        "title": "Implement Stripe Billing Integration",
        "description": "Configure Stripe client libraries and set up test/live api keys for payment flows.",
        "revenue_impact": 40,
        "security_impact": 0,
        "deployment_impact": 10,
        "recommended_agent": "Fintech Engineer",
        "dependency_order": 3
    },
    "Authentication flow is not implemented": {
        "title": "Implement User Authentication System",
        "description": "Set up secure sign-in, JWT session controls, and roles using Supabase Auth or native sessions.",
        "revenue_impact": 10,
        "security_impact": 40,
        "deployment_impact": 10,
        "recommended_agent": "Security Specialist",
        "dependency_order": 2
    },
    "Deployment descriptor (vercel.json, Dockerfile) is missing": {
        "title": "Create Deployment Configuration Files",
        "description": "Write standard deployment descriptors like Dockerfile, vercel.json, or docker-compose.yml.",
        "revenue_impact": 0,
        "security_impact": 10,
        "deployment_impact": 30,
        "recommended_agent": "Platform Engineer",
        "dependency_order": 2
    },
    "Missing project build manifests/package descriptors": {
        "title": "Create Project Package Manifests",
        "description": "Initialize package.json, requirements.txt, pyproject.toml, or Cargo.toml build descriptors.",
        "revenue_impact": 20,
        "security_impact": 0,
        "deployment_impact": 20,
        "recommended_agent": "Lead Swarm Orchestrator",
        "dependency_order": 1
    },
    "Missing repository assets": {
        "title": "Restore Repository Source Code",
        "description": "Populate missing source files, modules, and directories for project codebase.",
        "revenue_impact": 0,
        "security_impact": 0,
        "deployment_impact": 25,
        "recommended_agent": "Lead Swarm Orchestrator",
        "dependency_order": 1
    },
    "Missing monetization model definition": {
        "title": "Define Monetization Strategy",
        "description": "Formulate exact pricing models, API tier limits, or license agreements in markdown.",
        "revenue_impact": 15,
        "security_impact": 0,
        "deployment_impact": 0,
        "recommended_agent": "Lead Swarm Orchestrator",
        "dependency_order": 1
    },
    "Missing code repository": {
        "title": "Establish Project Git Repository",
        "description": "Initialize a fresh git repository and push basic project structure to tracking origin.",
        "revenue_impact": 0,
        "security_impact": 0,
        "deployment_impact": 30,
        "recommended_agent": "Lead Swarm Orchestrator",
        "dependency_order": 1
    },
    "Hardware telemetry schema not integrated": {
        "title": "Integrate IoT Telemetry Schema",
        "description": "Define AWS IoT Core message schema and write ingestion handlers for telemetry payloads.",
        "revenue_impact": 20,
        "security_impact": 10,
        "deployment_impact": 20,
        "recommended_agent": "IoT Specialist",
        "dependency_order": 2
    },
    "Active unmasked secret key exposure risk detected": {
        "title": "Remediate Unmasked Secret Keys",
        "description": "Audit code files to remove hardcoded API credentials and replace them with dynamic environment variables.",
        "revenue_impact": 0,
        "security_impact": 50,
        "deployment_impact": 0,
        "recommended_agent": "Security Specialist",
        "dependency_order": 1
    },
    "No automated test suite discovered": {
        "title": "Configure Automated Testing",
        "description": "Set up unit testing frameworks and write initial suite verifying system invariants.",
        "revenue_impact": 0,
        "security_impact": 0,
        "deployment_impact": 20,
        "recommended_agent": "Platform Engineer",
        "dependency_order": 2
    },
    "Epic Fury admin preview bypass is not implemented": {
        "title": "Implement Epic Fury Admin Preview Bypass",
        "description": "Create an entitlement helper in lib/entitlements.ts to support owner access bypass without Stripe customer payment.",
        "revenue_impact": 30,
        "security_impact": 10,
        "deployment_impact": 10,
        "recommended_agent": "Fintech Engineer",
        "dependency_order": 1
    },
    "Epic Fury Stripe test-mode bypass is not validated": {
        "title": "Configure Stripe Test-Mode Validation",
        "description": "Verify Epic Fury handles EPIC_FURY_STRIPE_TEST_MODE correctly to simulate subscriptions using test customer IDs.",
        "revenue_impact": 25,
        "security_impact": 5,
        "deployment_impact": 5,
        "recommended_agent": "Fintech Engineer",
        "dependency_order": 2
    },
    "Epic Fury public user payment enforcement is unverified": {
        "title": "Verify Public User Stripe Enforcement",
        "description": "Ensure normal public users are strictly gated and prompted to subscribe before accessing premium features.",
        "revenue_impact": 35,
        "security_impact": 20,
        "deployment_impact": 10,
        "recommended_agent": "Security Specialist",
        "dependency_order": 1
    }
}

def generate_queue():
    print("==================================================")
    print("GENERATING REVENUE ACTION QUEUE")
    print("==================================================")

    if not os.path.exists(RESULTS_PATH):
        print(f"[ERROR] Results file {RESULTS_PATH} not found!")
        return

    with open(RESULTS_PATH, "r", encoding="utf-8") as f:
        projects = json.load(f)

    # Use dynamic ISO 8601 UTC timestamp
    from datetime import timezone
    audit_timestamp = datetime.now(timezone.utc).isoformat()
    if not audit_timestamp.endswith("Z"):
        audit_timestamp += "Z"
    actions = []

    for proj in projects:
        project_id = proj.get("id", "")
        project_name = proj.get("name", "")
        blockers = proj.get("blockers", [])
        freshness_status = proj.get("freshness_status", "FRESH")
        
        project_actions = []

        # Convert blockers to actions
        for blk in blockers:
            meta = BLOCKER_MAPPING.get(blk, {
                "title": f"Resolve Blocker: {blk}",
                "description": f"Investigate and remediate the blocker: {blk}",
                "revenue_impact": 10,
                "security_impact": 10,
                "deployment_impact": 10,
                "recommended_agent": "Lead Swarm Orchestrator",
                "dependency_order": 2
            })
            
            # Form clean slug id
            slug = re.sub(r'[^a-z0-9]+', '-', meta["title"].lower()).strip('-')
            action_id = f"act-{project_id}-{slug}"
            
            total_impact = meta["revenue_impact"] + meta["security_impact"] + meta["deployment_impact"]
            if total_impact >= 50:
                urgency = "HIGH"
            elif total_impact >= 25:
                urgency = "MEDIUM"
            else:
                urgency = "LOW"
                
            evidence_links = []
            if proj.get("evidence_links"):
                evidence_links = list(proj["evidence_links"].values())
            if not evidence_links:
                evidence_links = ["docs/evidence/business/project-revenue-readiness-audit.md"]

            project_actions.append({
                "id": action_id,
                "project_id": project_id,
                "project_name": project_name,
                "title": meta["title"],
                "description": meta["description"],
                "blocker_source": blk,
                "revenue_impact": meta["revenue_impact"],
                "security_impact": meta["security_impact"],
                "deployment_impact": meta["deployment_impact"],
                "urgency": urgency,
                "dependency_order": meta["dependency_order"],
                "critical_path_rank": 999,  # Placeholder, filled post-sorting
                "recommended_agent": meta["recommended_agent"],
                "status": "READY",  # Adjusted below
                "evidence_links": evidence_links,
                "created_at": audit_timestamp,
                "last_verified_at": audit_timestamp,
                "freshness_status": freshness_status
            })

        # Apply Autopilot dependency/blocker resolution logic:
        # If any action in the project has dependency_order == 1, then all actions
        # with dependency_order > 1 are marked as "BLOCKED".
        has_dep_1 = any(act["dependency_order"] == 1 for act in project_actions)
        if has_dep_1:
            for act in project_actions:
                if act["dependency_order"] > 1:
                    act["status"] = "BLOCKED"
                    
        actions.extend(project_actions)

    # Sort actions using the tuple criteria requested:
    # 1. revenue_impact (descending)
    # 2. security_impact (descending)
    # 3. deployment_impact (descending)
    # 4. dependency_order (ascending)
    # 5. freshness_status (ascending: FRESH < STALE < DEGRADED)
    # 6. id (ascending) to guarantee stable sort
    
    def sort_key(act):
        # map freshness_status to order: FRESH=1, STALE=2, DEGRADED=3, UNKNOWN=4
        fresh_map = {"FRESH": 1, "STALE": 2, "DEGRADED": 3, "UNKNOWN": 4}
        fresh_val = fresh_map.get(act["freshness_status"], 4)
        return (
            -act["revenue_impact"],
            -act["security_impact"],
            -act["deployment_impact"],
            act["dependency_order"],
            fresh_val,
            act["id"]
        )

    actions.sort(key=sort_key)

    # Assign rank based on sorted order
    for idx, act in enumerate(actions, start=1):
        act["critical_path_rank"] = idx

    # Output JSON file
    os.makedirs(os.path.dirname(QUEUE_PATH), exist_ok=True)
    with open(QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(actions, f, indent=2)
    print(f"Saved revenue action queue to: {QUEUE_PATH}")

    # Generate Markdown evidence report
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("# HASF Revenue Action Queue Report (RC46)\n\n")
        f.write("**Date**: 2026-07-01  \n")
        f.write("**Auditor**: Antigravity Autopilot Queue Engine  \n")
        f.write(f"**Timestamp**: {audit_timestamp}  \n\n")
        
        f.write("## 1. Executive Summary\n")
        f.write("This queue prioritizes launch blockers and readiness gaps into a ranked, executable workflow. ")
        f.write("Critical path priority status resolves dynamic blockages recursively based on dependency order.\n\n")
        
        f.write("## 2. Prioritized Revenue Action Queue\n")
        f.write("| Rank | Project | Action Title | Recommended Agent | Revenue Impact | Security Impact | Deployment Impact | Status | Freshness |\n")
        f.write("| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")
        for act in actions:
            # Highlight top rank visually in table
            rank_str = f"**#{act['critical_path_rank']}**" if act['critical_path_rank'] == 1 else f"#{act['critical_path_rank']}"
            f.write(f"| {rank_str} | {act['project_name']} | {act['title']} | {act['recommended_agent']} | {act['revenue_impact']}% | {act['security_impact']}% | {act['deployment_impact']}% | **{act['status']}** | {act['freshness_status']} |\n")
        f.write("\n")
        
        f.write("## 3. Detailed Action Items\n")
        for act in actions:
            f.write(f"### Rank {act['critical_path_rank']}: {act['title']} ({act['project_name']})\n")
            f.write(f"- **ID**: `{act['id']}`\n")
            f.write(f"- **Description**: {act['description']}\n")
            f.write(f"- **Blocker Source**: `{act['blocker_source']}`\n")
            f.write(f"- **Impact metrics**: Revenue: `{act['revenue_impact']}%` | Security: `{act['security_impact']}%` | Deployment: `{act['deployment_impact']}%` (Urgency: `{act['urgency']}`)\n")
            f.write(f"- **Dependency Order**: `{act['dependency_order']}` | Status: **`{act['status']}`**\n")
            f.write(f"- **Recommended Agent**: `{act['recommended_agent']}`\n")
            f.write("- **Evidence / References**:\n")
            for link in act["evidence_links"]:
                f.write(f"  - [{os.path.basename(link)}](file://{os.path.join(PROJECT_ROOT, link)})\n")
            f.write("\n")
            
    print(f"Saved Markdown report to: {REPORT_PATH}")
    print("==================================================")
    print("QUEUE COMPILATION COMPLETE")
    print("==================================================")

if __name__ == "__main__":
    generate_queue()
