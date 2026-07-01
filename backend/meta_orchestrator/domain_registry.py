import os
from typing import Dict, List, Any

# Minimum required domains: 40+ as specified in prompt
DOMAINS = [
    "Runtime Truth", "Anti-Fake", "QA/Test", "Coding War Room", "SDLC", "DDLC",
    "Application Lifecycle", "Product Management", "Business Operations", "Chief of Staff",
    "Revenue/Sales", "Marketing", "Customer Success", "Support", "Training", "Finance",
    "Legal/Risk", "Privacy", "Cybersecurity", "AI Governance", "Data Management",
    "Knowledge Management", "Vendor/ToolOps", "SRE/Ops", "Business Continuity",
    "Disaster Recovery", "Evidence Management", "Release Management", "HomeOps",
    "FamilyOps", "Productivity", "Security Operations", "Incident Response",
    "Change Management", "Configuration Management", "Asset Management", "Compliance",
    "Procurement", "Pricing", "CRM/Pipeline", "Documentation", "Maintenance", "Retirement"
]

class DomainRegistry:
    def __init__(self):
        self.domains: Dict[str, Dict[str, Any]] = {}
        for d in DOMAINS:
            domain_id = d.lower().replace(" ", "_").replace("/", "_").replace("-", "_")
            
            # Map domain to specific specialized agents
            if d in ["Chief of Staff"]:
                owner = "chief_of_staff_agent"
            elif d in ["Runtime Truth"]:
                owner = "runtime_truth_agent"
            elif d in ["Anti-Fake"]:
                owner = "anti_fake_agent"
            elif d in ["QA/Test"]:
                owner = "qa_test_agent"
            elif d in ["SDLC", "DDLC", "Coding War Room", "Maintenance", "Retirement", "Documentation"]:
                owner = "refactor_agent"
            elif d in ["SRE/Ops", "Business Continuity", "Disaster Recovery", "Incident Response", "Change Management", "Configuration Management", "Asset Management"]:
                owner = "sre_agent"
            elif d in ["Product Management", "Business Operations", "Revenue/Sales", "Marketing", "Customer Success", "Support", "Training", "Finance", "Procurement", "Pricing", "CRM/Pipeline", "Productivity"]:
                owner = "business_ops_agent"
            elif d in ["Legal/Risk", "Privacy", "Cybersecurity", "AI Governance", "Security Operations", "Compliance", "Data Management", "Knowledge Management", "Vendor/ToolOps"]:
                owner = "security_agent"
            elif d in ["HomeOps", "FamilyOps"]:
                owner = "homeops_agent"
            elif d in ["Release Management", "Evidence Management", "Application Lifecycle"]:
                owner = "release_agent"
            else:
                owner = "general_agent"

            self.domains[domain_id] = {
                "domain_id": domain_id,
                "name": d,
                "owner_agent": owner,
                "backup_owner_agent": "chief_of_staff_agent",
                "escalation_path": "chief_of_staff_agent -> operator",
                "evidence_path": "docs/evidence/meta-orchestrator/domain-owner-assignment.md",
                "lifecycle_status": "ACTIVE",
                "charter": f"Core charter for {d}",
                "scope": f"All elements relating to {d}",
                "maturity_level": "LEVELED",
                "status": "ACTIVE",
                "evidence_paths": ["docs/evidence/meta-orchestrator/domain-owner-assignment.md"],
                "active_gaps": [],
                "missing_artifacts": [],
                "required_gates": [],
                "next_action": "Monitor domain health and run continuous gap scans.",
                "blocked_by": "",
                "risk_level": "MEDIUM",
                "revenue_relevance": "HIGH" if d in ["Revenue/Sales", "Pricing", "CRM/Pipeline"] else "MEDIUM",
                "operator_load_impact": 5.0,
                "runtime_truth_signal_ids": []
            }

    def get_all_domains(self) -> List[Dict[str, Any]]:
        return list(self.domains.values())

    def get_domain(self, domain_id: str) -> Dict[str, Any]:
        return self.domains.get(domain_id, {})

    def assign_owner(self, domain_id: str, owner_agent: str):
        if domain_id in self.domains:
            self.domains[domain_id]["owner_agent"] = owner_agent
            self.domains[domain_id]["status"] = "ACTIVE"

    def register_evidence(self, domain_id: str, path: str):
        if domain_id in self.domains:
            if path not in self.domains[domain_id]["evidence_paths"]:
                self.domains[domain_id]["evidence_paths"].append(path)
