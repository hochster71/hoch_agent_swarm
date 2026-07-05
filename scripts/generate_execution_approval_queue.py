#!/usr/bin/env python3
# scripts/generate_execution_approval_queue.py
# Generates the autonomous execution approval queue for HAS/HASF.

import os
import json
import datetime
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "has_live_project_tracker" / "data"

OUTPUT_JSON = DATA_DIR / "hoch_execution_approval_queue.json"
OUTPUT_MD = PROJECT_ROOT / "docs/evidence/runtime/hoch-execution-approval-queue.md"

def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def main():
    print("==================================================")
    print("GENERATING SWARM EXECUTION APPROVAL QUEUE")
    print("==================================================")

    # 1. Load context data
    leadership = load_json(DATA_DIR / "ai_executive_leadership.json")
    finance = load_json(DATA_DIR / "finance_agent_assignments.json")
    schedule = load_json(DATA_DIR / "hoch_pod_schedule.json")
    actions = load_json(DATA_DIR / "revenue_action_queue.json")
    runtime = load_json(DATA_DIR / "hoch_pods_runtime_state.json")
    inventory = load_json(DATA_DIR / "project_inventory.json")

    # Helper to find executive title by role_id
    def get_exec_title(role_id):
        for lead in leadership:
            if lead.get("role_id") == role_id:
                return lead.get("title")
        return "None"

    # Helper to find finance agent title by agent_id
    def get_fin_title(agent_id):
        for agent in finance:
            if agent.get("agent_id") == agent_id:
                return agent.get("title")
        return "None"

    # Read existing approval statuses if queue already exists
    existing_queue = load_json(OUTPUT_JSON)
    existing_status = {}
    for item in existing_queue:
        existing_status[item.get("proposal_id")] = item.get("approval_status")

    # Define deterministic template proposals matched to pods
    proposals_template = [
        {
            "proposal_id": "prop-cyber-gitleaks",
            "pod_id": "pod-cyber",
            "pod_name": "Cyber Pod",
            "executive_role_id": "security_officer",
            "finance_role_id": "fintech_compliance_advisor",
            "project_id": "hoch-agent-swarm",
            "project_name": "Hoch Agent Swarm / HASF",
            "action_title": "Scan Codebase for Secrets Exposure",
            "action_description": "Execute local GitLeaks scan on the repository to prevent unmasked secret key leakage.",
            "action_type": "READ_ONLY",
            "risk_level": "LOW",
            "execution_mode": "SAFE",
            "approval_required": False,
            "allowed_without_approval": True,
            "blocked_reason": "",
            "affected_paths": ["/"],
            "affected_services": ["git-leaks"],
            "external_impact": "None (local process run only)",
            "secret_access_required": False,
            "network_access_required": False,
            "rollback_plan": "Not required for read-only static scanning.",
            "verification_plan": "Verify scan exit code is 0."
        },
        {
            "proposal_id": "prop-qa-playwright",
            "pod_id": "pod-qa",
            "pod_name": "QA Pod",
            "executive_role_id": "qa_release",
            "finance_role_id": "revenue_evidence_collector",
            "project_id": "hoch-agent-swarm",
            "project_name": "Hoch Agent Swarm / HASF",
            "action_title": "Run Local Playwright Integration Suite",
            "action_description": "Run local E2E specs tests verifying telemetry cockpit panels.",
            "action_type": "LOCAL_SAFE_WRITE",
            "risk_level": "LOW",
            "execution_mode": "SAFE",
            "approval_required": False,
            "allowed_without_approval": True,
            "blocked_reason": "",
            "affected_paths": ["tests/e2e/"],
            "affected_services": ["playwright"],
            "external_impact": "None (local browser automation test)",
            "secret_access_required": False,
            "network_access_required": False,
            "rollback_plan": "Not required for local stateless tests.",
            "verification_plan": "Inspect HTML run reports for 0 failures."
        },
        {
            "proposal_id": "prop-builder-compile",
            "pod_id": "pod-builder",
            "pod_name": "Builder Pod",
            "executive_role_id": "tech_director",
            "finance_role_id": "None",
            "project_id": "hoch-agent-swarm",
            "project_name": "Hoch Agent Swarm / HASF",
            "action_title": "TypeScript Production Build Compilation",
            "action_description": "Compile the production bundle and generate type-checking reports.",
            "action_type": "LOCAL_SAFE_WRITE",
            "risk_level": "MEDIUM",
            "execution_mode": "SAFE",
            "approval_required": True,
            "allowed_without_approval": False,
            "blocked_reason": "",
            "affected_paths": ["backend/"],
            "affected_services": ["tsc", "vite"],
            "external_impact": "Generates static build bundle on node filesystem.",
            "secret_access_required": False,
            "network_access_required": False,
            "rollback_plan": "Clean target dist/ folder and rebuild from source.",
            "verification_plan": "Run build artifacts and check presence of main.js."
        },
        {
            "proposal_id": "prop-revenue-stripe",
            "pod_id": "pod-revenue",
            "pod_name": "Revenue Pod",
            "executive_role_id": "cfo",
            "finance_role_id": "stripe_monetization_controller",
            "project_id": "hoch-hasf-soccer",
            "project_name": "HOCH HASF Soccer Intelligence Platform",
            "action_title": "Stripe Live Key Sandbox Initialization",
            "action_description": "Provision live API keys for HOCH HASF Soccer monetization pipeline.",
            "action_type": "STRIPE_LIVE_CONFIG",
            "risk_level": "CRITICAL",
            "execution_mode": "UNSAFE",
            "approval_required": True,
            "allowed_without_approval": False,
            "blocked_reason": "Stripe live configurations always require explicit Michael Hoch approval",
            "affected_paths": [".env"],
            "affected_services": ["stripe-cli"],
            "external_impact": "Configures live payment gateway settings.",
            "secret_access_required": True,
            "network_access_required": False,
            "rollback_plan": "Remove secret live keys and restore backup env template.",
            "verification_plan": "Verify Stripe signature check validates locally."
        },
        {
            "proposal_id": "prop-deploy-vercel",
            "pod_id": "pod-deploy",
            "pod_name": "Deploy Pod",
            "executive_role_id": "coo",
            "finance_role_id": "None",
            "project_id": "epic-fury-2026",
            "project_name": "Epic Fury 2026",
            "action_title": "Deploy Production Image to Cloud Run",
            "action_description": "Trigger Docker build and deploy to Vercel/Cloud Run for Epic Fury 2026.",
            "action_type": "DEPLOYMENT",
            "risk_level": "CRITICAL",
            "execution_mode": "UNSAFE",
            "approval_required": True,
            "allowed_without_approval": False,
            "blocked_reason": "Deployments to production environments always require Michael Hoch signature",
            "affected_paths": ["Dockerfile", "vercel.json"],
            "affected_services": ["docker-cli", "vercel-cli"],
            "external_impact": "Releases new application version to public internet domain.",
            "secret_access_required": True,
            "network_access_required": True,
            "rollback_plan": "Revert to previous working deployment tag version.",
            "verification_plan": "Run staging health probe checking endpoint return 200."
        },
        {
            "proposal_id": "prop-research-scrape",
            "pod_id": "pod-research",
            "pod_name": "Research Pod",
            "executive_role_id": "product_officer",
            "finance_role_id": "hasf_product_finance_manager",
            "project_id": "hoch-hasf-soccer",
            "project_name": "HOCH HASF Soccer Intelligence Platform",
            "action_title": "Web Scrape Soccer Training Metadata",
            "action_description": "Perform bulk scraping of external coaching sites to update recommended drills.",
            "action_type": "NETWORK_WRITE",
            "risk_level": "HIGH",
            "execution_mode": "SAFE",
            "approval_required": True,
            "allowed_without_approval": False,
            "blocked_reason": "External network write actions require administrative sign-off",
            "affected_paths": ["has_live_project_tracker/data/"],
            "affected_services": ["fetch-url"],
            "external_impact": "Sends outgoing HTTP requests to target remote APIs.",
            "secret_access_required": False,
            "network_access_required": True,
            "rollback_plan": "Wipe scraped json records cache.",
            "verification_plan": "Run json structure validity linter."
        },
        {
            "proposal_id": "prop-audit-purge",
            "pod_id": "pod-audit",
            "pod_name": "Audit Pod",
            "executive_role_id": "chief_of_staff",
            "finance_role_id": "None",
            "project_id": "None",
            "project_name": "None",
            "action_title": "Purge Historical Database Log Archives",
            "action_description": "Delete sqlite3 database logs older than 90 days.",
            "action_type": "DESTRUCTIVE",
            "risk_level": "CRITICAL",
            "execution_mode": "UNSAFE",
            "approval_required": True,
            "allowed_without_approval": False,
            "blocked_reason": "Destructive database purge actions are denied by default under safe-write policy",
            "affected_paths": ["has_live_project_tracker/data/global_project_registry.sqlite"],
            "affected_services": ["sqlite3-cli"],
            "external_impact": "Irreversible loss of local historical telemetry data.",
            "secret_access_required": False,
            "network_access_required": False,
            "rollback_plan": "Restore database backup snapshot.",
            "verification_plan": "Verify row count matching."
        }
    ]

    proposals = []
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

    schedule_list = schedule.get("schedule", []) if isinstance(schedule, dict) else schedule
    for temp in proposals_template:
        # Find scheduled node from pod schedule
        node_name = "None"
        for pod in schedule_list:
            if isinstance(pod, dict) and pod.get("pod_id") == temp["pod_id"]:
                node_name = pod.get("assigned_node_name", "None")

        # Set approval status
        # 1. Maintain existing status if already simulated
        # 2. Otherwise default based on policy
        prop_id = temp["proposal_id"]
        status = "PENDING"
        if prop_id in existing_status:
            status = existing_status[prop_id]
        elif temp["action_type"] == "READ_ONLY" or temp["action_type"] == "LOCAL_SAFE_WRITE" and not temp["approval_required"]:
            status = "APPROVED"
        elif temp["action_type"] == "DESTRUCTIVE":
            status = "REJECTED"

        prop = {
            "proposal_id": prop_id,
            "pod_id": temp["pod_id"],
            "pod_name": temp["pod_name"],
            "executive_owner": get_exec_title(temp["executive_role_id"]),
            "finance_or_product_owner": get_fin_title(temp["finance_role_id"]),
            "project_id": temp["project_id"],
            "project_name": temp["project_name"],
            "scheduled_node": node_name,
            "action_title": temp["action_title"],
            "action_description": temp["action_description"],
            "action_type": temp["action_type"],
            "risk_level": temp["risk_level"],
            "execution_mode": temp["execution_mode"],
            "approval_required": temp["approval_required"],
            "approval_status": status,
            "allowed_without_approval": temp["allowed_without_approval"],
            "blocked_reason": temp["blocked_reason"],
            "affected_paths": temp["affected_paths"],
            "affected_services": temp["affected_services"],
            "external_impact": temp["external_impact"],
            "secret_access_required": temp["secret_access_required"],
            "network_access_required": temp["network_access_required"],
            "rollback_plan": temp["rollback_plan"],
            "verification_plan": temp["verification_plan"],
            "evidence_links": [
                "docs/security/hoch-pods-safe-write-policy.md",
                "docs/evidence/runtime/hoch-execution-approval-queue.md"
            ],
            "created_at": timestamp,
            "last_verified_at": timestamp,
            "freshness_status": "FRESH"
        }
        proposals.append(prop)

    # Write output JSON
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(proposals, f, indent=2)
    print(f"[PASS] Saved execution approval queue to: {OUTPUT_JSON}")

    # Write output Markdown evidence brief
    os.makedirs(os.path.dirname(OUTPUT_MD), exist_ok=True)
    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("# HOCH Swarm Execution Approval Queue Evidence\n\n")
        f.write(f"**Generated**: {timestamp}  \n")
        f.write("**Zero-Trust Execution Gates Status**: ACTIVE  \n\n")
        
        f.write("### Active Proposals Summary\n\n")
        f.write("| ID | Pod | Action Title | Type | Risk | Status | Allowed Without Approval |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for p in proposals:
            allowed_str = "Yes" if p["allowed_without_approval"] else "No"
            f.write(f"| `{p['proposal_id']}` | {p['pod_name']} | {p['action_title']} | {p['action_type']} | **{p['risk_level']}** | {p['approval_status']} | {allowed_str} |\n")
        
        f.write("\n### Zero-Trust Policy Audit Log\n\n")
        for p in proposals:
            f.write(f"#### `{p['proposal_id']}`: {p['action_title']}\n")
            f.write(f"- **Executive Owner**: {p['executive_owner']}\n")
            f.write(f"- **Finance/Product Owner**: {p['finance_or_product_owner']}\n")
            f.write(f"- **Risk Level**: {p['risk_level']}\n")
            f.write(f"- **Type**: {p['action_type']}\n")
            f.write(f"- **Status**: {p['approval_status']}\n")
            if p["blocked_reason"]:
                f.write(f"- **Blocked Reason**: *{p['blocked_reason']}*\n")
            f.write(f"- **Verification**: `{p['verification_plan']}`\n")
            f.write(f"- **Rollback**: `{p['rollback_plan']}`\n\n")

    print(f"[PASS] Generated execution approval evidence brief: {OUTPUT_MD}")
    print("==================================================")

if __name__ == "__main__":
    main()
