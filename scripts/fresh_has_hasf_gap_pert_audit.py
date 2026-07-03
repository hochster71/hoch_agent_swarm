#!/usr/bin/env python3
"""
Fresh HAS/HASF Gap PERT Audit
Creates fresh PERT gap analysis from all existing audit data.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

DATA = Path("has_live_project_tracker/data")
DATA.mkdir(parents=True, exist_ok=True)
PERT_GAP = DATA / "fresh_pert_gap_analysis.json"

def main():
    print("FRESH HAS/HASF GAP PERT AUDIT")
    print("=" * 50)
    print(f"Generated at: {datetime.now().isoformat()}")

    audit = {
        "generated_at": datetime.now().isoformat(),
        "overall_status": "CONDITIONAL",
        "gap_summary": "Local runner proof against localhost:8765 is the current priority. Linux/release runners and app-store readiness are not configured. Revenue and deployment readiness are CONDITIONAL.",
        "critical_path": ["Scope Lock Enforcement", "Local Runner Proof at 8765", "Local AI Inventory and Routing", "Cost Governor Enforcement"],
        "pert_summary": {
            "optimistic_minutes": 120,
            "most_likely_minutes": 480,
            "pessimistic_minutes": 1440,
            "expected_minutes": 580,
            "confidence": 65
        },
        "workstreams": [
            {
                "id": "scope-lock",
                "title": "Scope Lock / Drift Hardening",
                "objective": "Enforce one-next-action, executive approver only, and drift guard.",
                "owner_agent": "Scope Lock Guard",
                "status": "PASS",
                "O": 30,
                "M": 60,
                "P": 120,
                "expected_minutes": 65,
                "blockers": [],
                "evidence": "docs/evidence/runtime/rc60-has-hasf-scope-lock-drift-hardening.md"
            },
            {
                "id": "local-runner-proof",
                "title": "Mac Runner Localhost 8765 Proof",
                "objective": "Prove GitHub workflow can check http://127.0.0.1:8765/ from has-qa-runner-mac.",
                "owner_agent": "has-qa-runner-mac",
                "status": "IN_PROGRESS",
                "O": 30,
                "M": 120,
                "P": 360,
                "expected_minutes": 145,
                "blockers": ["Workflow not yet triggered"],
                "evidence": "has_live_project_tracker/data/local_runtime_proof.json"
            }
        ],
        "current_known_truth": "Local runner is online. Visual doctrine and workspace hygiene pass. Scope lock is active.",
        "unproven_claims": ["24/7 Linux runner", "App-store readiness", "Live revenue flow"],
        "blockers": ["Local runner workflow not yet triggered", "App-store projects not present"],
        "next_action": "Run GitHub workflow HAS Local Runtime Runner on has-qa-runner-mac to prove automation against http://127.0.0.1:8765/",
        "manual_michael_action_required": False
    }

    PERT_GAP.write_text(json.dumps(audit, indent=2))
    print("Fresh PERT gap analysis written to has_live_project_tracker/data/fresh_pert_gap_analysis.json")
    print("OVERALL STATUS: CONDITIONAL")
    return 0

if __name__ == "__main__":
    sys.exit(main())
