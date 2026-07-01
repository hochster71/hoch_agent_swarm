import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from backend.prompt_registry import get_registry

# Define the Route chains (ID arrays)
ROUTE_CHAINS = {
    "coding": ["CODE-001", "CODE-002", "SAST-001", "QA-001", "REL-004"],
    "cybersecurity": ["THREAT-002", "SAST-001", "DAST-002", "AUD-002", "AUD-003", "REL-004"],
    "ai_safety": ["AI-001", "AIRT-016", "BREAK-021", "EXCEPT-022"],
    "privacy": ["PRIV-003", "UXSEC-020"],
    "release": ["QA-001", "DEV-002", "REL-004"],
    "ambiguous": ["CODE-001", "QA-001", "AUD-002"],
    "pentest": ["PENTEST-007", "VULN-005", "PATCH-006", "QA-001", "REL-004"]
}

class PromptRouter:
    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            base_dir = Path(__file__).parent.parent
        self.base_dir = base_dir
        self.registry = get_registry()

    def get_rules(self) -> Dict[str, Any]:
        return {
            "version": "0.1.0",
            "routing_policies": {
                "coding": "Principal Software Architect -> Full-Stack Builder Agent -> Static Code Security Reviewer -> QA Test Strategy Architect -> Release Readiness Gatekeeper",
                "cybersecurity": "Threat Modeling Agent -> Static Code Security Reviewer / API DAST Agent -> Control Gap Analyst -> Continuous Monitoring Auditor -> Release Readiness Gatekeeper",
                "ai_safety": "AI Model Risk QA Agent -> Red Team Prompt Agent -> Build Breaker Agent -> Exception Risk Board Agent",
                "privacy": "Privacy Engineering Agent -> Secure UX Review Agent -> Human Approval Gate",
                "release": "QA Test Strategy Architect -> SBOM and SCA Agent -> Release Readiness Gatekeeper -> Human Approval Gate",
                "pentest": "Pen Test Report Translator -> Vulnerability Triage Agent -> Patch Management Agent -> Validation Tests -> Release Readiness Gatekeeper",
                "ambiguous": "Principal Software Architect -> QA Test Strategy Architect -> Control Gap Analyst"
            },
            "risk_rules": {
                "triggers": ["delete", "deploy", "publish", "production", "secrets", "credentials", "firewall", "router", "network security", "money", "family", "private data"]
            }
        }

    def plan_route(self, task_description: str, risk_level: str = "LOW") -> Dict[str, Any]:
        task_lower = task_description.lower()

        # Check fail-closed triggers
        fail_closed_triggers = []
        blocked_actions = []
        
        # 1. Prompt library check
        if not self.registry.prompts or self.registry.status == "FAIL_CLOSED":
            fail_closed_triggers.append("PROMPT_LIBRARY_UNAVAILABLE")
            blocked_actions.append("ROUTE_PLANNING_BLOCKED")

        # 2. Bypass / ignore safety checks
        if any(kw in task_lower for kw in ["bypass approval", "ignore security", "skip approval", "no approval"]):
            fail_closed_triggers.append("BYPASS_APPROVAL_ATTEMPTED")
            blocked_actions.append("TASK_EXECUTION_BLOCKED")

        if any(kw in task_lower for kw in ["delete without approval", "publish without approval", "deploy without approval"]):
            fail_closed_triggers.append("DESTRUCTIVE_UNAUTHORIZED_ACTION")
            blocked_actions.append("TASK_EXECUTION_BLOCKED")

        # Determine task category/chain type
        chain_key = "ambiguous"
        mission_type = "AMBIGUOUS"

        if any(kw in task_lower for kw in ["pen test", "pentest", "zap", "nessus", "scan report", "vulnerabilities report"]):
            chain_key = "pentest"
            mission_type = "PEN_TEST_TRIAGE"
        elif any(kw in task_lower for kw in ["cyber", "security", "hardening", "vulnerability", "incident"]):
            chain_key = "cybersecurity"
            mission_type = "CYBER_SECURITY"
        elif any(kw in task_lower for kw in ["prompt safety", "jailbreak", "red team", "ai risk", "risk qa", "breaker"]):
            chain_key = "ai_safety"
            mission_type = "AI_SAFETY"
        elif any(kw in task_lower for kw in ["code", "coding", "build", "program", "develop"]):
            chain_key = "coding"
            mission_type = "CODING"
        elif any(kw in task_lower for kw in ["family", "private data", "home", "privacy"]):
            chain_key = "privacy"
            mission_type = "PRIVACY_AND_HOME"
        elif any(kw in task_lower for kw in ["app-store", "app store", "release", "deployment"]):
            chain_key = "release"
            mission_type = "RELEASE_MANAGEMENT"

        # Determine prompt chain IDs and verify presence in registry
        selected_ids = ROUTE_CHAINS.get(chain_key, [])
        
        # Verify IDs exist in registry
        missing_ids = []
        for pid in selected_ids:
            if not any(p["id"] == pid for p in self.registry.prompts):
                missing_ids.append(pid)

        if missing_ids:
            fail_closed_triggers.append(f"MISSING_PROMPT_IDS: {', '.join(missing_ids)}")
            blocked_actions.append("TASK_EXECUTION_BLOCKED")

        # Check if task contains high-risk ambiguity
        if chain_key == "ambiguous" and risk_level in ["HIGH", "CRITICAL"]:
            fail_closed_triggers.append("UNRESOLVED_HIGH_RISK_AMBIGUITY")
            blocked_actions.append("TASK_EXECUTION_BLOCKED")

        # Determine risk level based on keywords
        calculated_risk = risk_level
        if calculated_risk == "LOW":
            if any(kw in task_lower for kw in ["delete", "deploy", "publish", "production", "secrets", "credentials", "firewall", "router", "network security", "money"]):
                calculated_risk = "HIGH"
            elif any(kw in task_lower for kw in ["family", "private data", "home", "privacy"]):
                calculated_risk = "MEDIUM"

        if fail_closed_triggers:
            calculated_risk = "FAIL_CLOSED"

        # Determine human approval requirements
        human_approval_required = False
        if calculated_risk in ["HIGH", "CRITICAL", "FAIL_CLOSED"]:
            human_approval_required = True
        elif any(kw in task_lower for kw in [
            "delete", "deploy", "publish", "production", "app store", "app-store",
            "external publishing", "secrets", "credentials", "firewall", "router",
            "network security", "spending money", "money", "family", "private data"
        ]):
            human_approval_required = True

        selected_prompts = []
        selected_titles = []
        for pid in selected_ids:
            for p in self.registry.prompts:
                if p["id"] == pid:
                    selected_prompts.append(p)
                    selected_titles.append(p["title"])
                    break

        plan = {
            "status": "ROUTE_PLAN_ONLY",
            "execution_allowed": False,
            "mission_type": mission_type,
            "risk_level": calculated_risk,
            "selected_prompt_ids": selected_ids,
            "selected_prompt_titles": selected_titles,
            "governance_wrapper_required": True,
            "human_approval_required": human_approval_required,
            "fail_closed_triggers": fail_closed_triggers,
            "evidence_required": [
                "prompt_router_report.json",
                "evidence_manifest.json"
            ],
            "blocked_actions": blocked_actions,
            "next_recommended_phase": "human_review_or_phase_4_approval_gate"
        }

        # Write report
        self.write_report(task_description, plan)
        return plan

    def write_report(self, task_description: str, plan: Dict[str, Any]):
        report_dir = self.base_dir / "artifacts" / "qa" / "prompt_router"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / "prompt_router_report.json"
        
        report = {
            "task_description": task_description,
            "plan": plan
        }
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

_router_instance = None

def get_router() -> PromptRouter:
    global _router_instance
    if _router_instance is None:
        _router_instance = PromptRouter()
    return _router_instance
