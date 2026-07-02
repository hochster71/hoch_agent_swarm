import math
from datetime import datetime

# Seeding the lanes data
SEED_LANES = [
    {
        "id": "A",
        "name": "Michael AI Model / HELM",
        "description": "Michael AI operational learning and HELM execution persona",
        "status": "Active",
        "owner_agent": "HELM",
        "optimistic_minutes": 45,
        "most_likely_minutes": 90,
        "pessimistic_minutes": 180,
        "dependencies": [],
        "critical": True,
        "blocked": False,
        "stale": False,
        "evidence_refs": ["docs/evidence/helm/20260702-1634-helm-onboarding.md"],
        "commit_refs": ["f5136b3"],
        "next_action": "Validate Michael AI Model inside canonical Docker runtime"
    },
    {
        "id": "B",
        "name": "HOCH-200 Runtime Truth + Restart Survival",
        "description": "Verify host configurations, VPS tunnel setup, and survive reboot",
        "status": "Active",
        "owner_agent": "capt-guardrail",
        "optimistic_minutes": 30,
        "most_likely_minutes": 75,
        "pessimistic_minutes": 150,
        "dependencies": ["E"],
        "critical": True,
        "blocked": False,
        "stale": False,
        "evidence_refs": ["docs/evidence/vps/20260702-1557-hoch200-vps-verification.md"],
        "commit_refs": ["927157b"],
        "next_action": "Harden VPS SSH key-exchange policy and local restart systemd/launchd daemons"
    },
    {
        "id": "C",
        "name": "Moonshot UI Remote Route",
        "description": "Proxy local Moonshot UI securely to remote Tailscale network",
        "status": "Accepted",
        "owner_agent": "frontend-swarm-ui-agent",
        "optimistic_minutes": 10,
        "most_likely_minutes": 20,
        "pessimistic_minutes": 40,
        "dependencies": [],
        "critical": False,
        "blocked": False,
        "stale": False,
        "evidence_refs": ["docs/evidence/ui/20260702-1630-moonshot-remote-ui-route.md"],
        "commit_refs": ["7d72e46"],
        "next_action": "Monitor tunnel health check and packet loss"
    },
    {
        "id": "D",
        "name": "GitHub Linux/macOS QA Runners",
        "description": "Dual-runner CI/CD configuration to enforce QA parity",
        "status": "Active",
        "owner_agent": "ms-checkmark",
        "optimistic_minutes": 45,
        "most_likely_minutes": 90,
        "pessimistic_minutes": 180,
        "dependencies": ["B"],
        "critical": True,
        "blocked": False,
        "stale": False,
        "evidence_refs": ["docs/evidence/ci/20260702-1640-github-linux-runner-qa.md"],
        "commit_refs": ["a1322aa"],
        "next_action": "Merge Linux QA workflow and verify on public repository"
    },
    {
        "id": "E",
        "name": "Runtime Truth / Final Verifier",
        "description": "Integrate Final Verifier rules and audit database truth tables",
        "status": "Active",
        "owner_agent": "prof-ledger",
        "optimistic_minutes": 30,
        "most_likely_minutes": 60,
        "pessimistic_minutes": 120,
        "dependencies": ["A"],
        "critical": True,
        "blocked": False,
        "stale": False,
        "evidence_refs": ["docs/evidence/runtime/hoch-pods-runtime-evidence.md"],
        "commit_refs": ["2276b96"],
        "next_action": "Resolve coding_defects database schema constraint"
    },
    {
        "id": "F",
        "name": "HAS/HASF Ace Knowledge Graph",
        "description": "Interactive visualization mapping HAS and HASF architecture and gates",
        "status": "Planned",
        "owner_agent": "product-strategy-agent",
        "optimistic_minutes": 30,
        "most_likely_minutes": 60,
        "pessimistic_minutes": 120,
        "dependencies": ["C"],
        "critical": False,
        "blocked": False,
        "stale": False,
        "evidence_refs": [],
        "commit_refs": [],
        "next_action": "Add Cytoscape/VisJS component to Moonshot UI"
    },
    {
        "id": "G",
        "name": "Autonomy Loop / Local Worker Recovery",
        "description": "Initiate worker discovery, check node health, and resolve local cluster assignments",
        "status": "Pending",
        "owner_agent": "agent-runtime-engineer",
        "optimistic_minutes": 60,
        "most_likely_minutes": 120,
        "pessimistic_minutes": 240,
        "dependencies": ["D"],
        "critical": True,
        "blocked": False,
        "stale": True,
        "evidence_refs": [],
        "commit_refs": [],
        "next_action": "Provision local k3s sidecar nodes"
    },
    {
        "id": "H",
        "name": "HASF Revenue Packaging",
        "description": "Package Swarm capabilities into Stripe-connected monetization lanes",
        "status": "Pending",
        "owner_agent": "boss-noodle",
        "optimistic_minutes": 60,
        "most_likely_minutes": 120,
        "pessimistic_minutes": 240,
        "dependencies": ["G"],
        "critical": True,
        "blocked": False,
        "stale": False,
        "evidence_refs": [],
        "commit_refs": [],
        "next_action": "Integrate checkout links with HASF backend billing"
    },
    {
        "id": "I",
        "name": "Apple Telemetry / Device Swarm",
        "description": "Retrieve Apple product telemetry metrics from local devices",
        "status": "Partial",
        "owner_agent": "dr-signal",
        "optimistic_minutes": 20,
        "most_likely_minutes": 45,
        "pessimistic_minutes": 90,
        "dependencies": [],
        "critical": False,
        "blocked": False,
        "stale": False,
        "evidence_refs": ["docs/evidence/device_telemetry/20260702-1606-apple-product-telemetry.md"],
        "commit_refs": ["4b198e2"],
        "next_action": "Label dynamic device records"
    },
    {
        "id": "J",
        "name": "Old UI Cleanup / Deprecation",
        "description": "Remove old 8080 and 3012 endpoints and code templates",
        "status": "Parked",
        "owner_agent": "backend-platform-agent",
        "optimistic_minutes": 30,
        "most_likely_minutes": 75,
        "pessimistic_minutes": 180,
        "dependencies": [],
        "critical": False,
        "blocked": False,
        "stale": False,
        "evidence_refs": [],
        "commit_refs": [],
        "next_action": "Clean static files under frontend/archive"
    }
]

def calculate_pert_estimates(lanes):
    calculated = []
    for l in lanes:
        opt = l["optimistic_minutes"]
        ml = l["most_likely_minutes"]
        pes = l["pessimistic_minutes"]
        
        expected = (opt + 4 * ml + pes) / 6.0
        variance = ((pes - opt) / 6.0) ** 2
        
        lane_copy = dict(l)
        lane_copy["expected_minutes"] = round(expected, 1)
        lane_copy["variance"] = round(variance, 2)
        calculated.append(lane_copy)
    return calculated

def get_goal_pert_analysis():
    lanes_with_estimates = calculate_pert_estimates(SEED_LANES)
    
    # Calculate critical path (A -> E -> B -> D -> G -> H)
    critical_ids = ["A", "E", "B", "D", "G", "H"]
    critical_lanes = [l for l in lanes_with_estimates if l["id"] in critical_ids]
    
    expected_completion = sum(l["expected_minutes"] for l in critical_lanes)
    
    stale_count = sum(1 for l in lanes_with_estimates if l["stale"])
    blocked_count = sum(1 for l in lanes_with_estimates if l["blocked"])
    
    # Confidence level heuristic based on progress
    # If key critical tasks are Completed/Active vs Pending/Stale
    completed_critical = sum(1 for l in critical_lanes if l["status"] in ["Active", "Completed", "Accepted"])
    ratio = completed_critical / len(critical_lanes)
    if ratio > 0.8:
        confidence = "High"
    elif ratio > 0.5:
        confidence = "Medium-high"
    else:
        confidence = "Medium"
        
    return {
        "goal_id": "HAS-HASF-GOAL",
        "goal_name": "/GOAL",
        "north_star": "Complete HAS/HASF as an operational, verified, AI-assisted command system that reduces Michael’s workload, proves runtime truth, routes work safely, packages capabilities, and moves toward revenue without fake-green claims.",
        "status": "NO-GO",
        "final_verifier": "BLOCKED",
        "readiness_score": 50,
        "active_blocker": "NO_ACTIVE_RELEASE_GO",
        "active_blockers": ["NO_ACTIVE_RELEASE_GO"],
        "critical_path": critical_ids,
        "expected_completion_minutes": round(expected_completion, 1),
        "confidence": confidence,
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "evidence_refs": [
            "docs/evidence/helm/20260702-1634-helm-onboarding.md",
            "docs/evidence/vps/20260702-1557-hoch200-vps-verification.md",
            "docs/evidence/ui/20260702-1630-moonshot-remote-ui-route.md",
            "docs/evidence/ci/20260702-1640-github-linux-runner-qa.md"
        ],
        "commit_refs": ["f5136b3", "927157b", "7d72e46", "a1322aa"],
        "next_safe_action": "Canonical Docker verification + HOCH-200 restart survival",
        "lanes": lanes_with_estimates,
        "summary_metrics": {
            "stale_tasks": stale_count,
            "blocked_tasks": blocked_count,
            "total_critical_variance": round(sum(l["variance"] for l in critical_lanes), 2)
        }
    }
