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
            self.domains[domain_id] = {
                "domain_id": domain_id,
                "name": d,
                "owner_agent": "unassigned" if d not in ["Chief of Staff", "Runtime Truth", "Anti-Fake", "QA/Test"] else d.lower().replace(" ", "_").replace("/", "_").replace("-", "_") + "_agent",
                "charter": f"Core charter for {d}",
                "scope": f"All elements relating to {d}",
                "maturity_level": "INITIAL" if d not in ["Runtime Truth", "Anti-Fake", "QA/Test", "Chief of Staff"] else "LEVELED",
                "status": "INITIALIZED" if d not in ["Runtime Truth", "Anti-Fake", "QA/Test", "Chief of Staff"] else "ACTIVE",
                "evidence_paths": [],
                "active_gaps": [],
                "missing_artifacts": [],
                "required_gates": [],
                "next_action": "Run gap discovery scan to identify next-best actions.",
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
            self.domains[domain_id]["status"] = "OWNED"

    def register_evidence(self, domain_id: str, path: str):
        if domain_id in self.domains:
            if path not in self.domains[domain_id]["evidence_paths"]:
                self.domains[domain_id]["evidence_paths"].append(path)
