import re
from typing import Dict, Any, Optional

class AgentTaskClassifier:
    def __init__(self):
        self.domains = {
            "Incident-Response": ["incident", "contain", "mitigate", "triage", "exfil", "attack", "compromise"],
            "Cloud-Security": ["aws", "gcp", "azure", "cloud", "s3", "iam", "bucket"],
            "Vulnerability-Management": ["vulnerability", "vuln", "patch", "cve", "epss", "kev", "remediat"],
            "Data-Security": ["data classification", "encrypt", "at rest", "in transit", "handling", "pii"],
            "Privacy": ["privacy", "gdpr", "ccpa", "dpia", "minimization", "consent"],
            "Security-Architecture": ["architecture", "skill registry", "gate", "runtime policy"],
            "Infrastructure-Hardware": ["port", "firewall", "lan", "exposure", "ufw", "pf", "listening"],
            "Audit": ["audit", "compliance", "verification", "check", "control", "report"],
            "Self-Healing": ["self-healing", "ephemeral", "ttl", "teardown", "zombie"],
            "Family-Personal": ["family", "home", "kid", "play", "personal", "parent", "household"],
            "QA": ["test", "verify", "qa", "regression", "smoke", "golden fixture"],
            "DevSecOps": ["pipeline", "cicd", "gitlab", "jenkins", "build", "provenance"],
            "SAST": ["sast", "static analysis", "lint", "code scan"],
            "DAST": ["dast", "dynamic analysis", "zap", "spider", "fuzz"],
            "Coding": ["code", "refactor", "bug", "syntax", "develop"],
            "Supply-Chain": ["sbom", "dependency", "provenance", "typosquat", "vendor", "third party"]
        }
        
        self.industries = {
            "Defense / DoD / National Security": ["dod", "military", "defense", "national security", "rmf", "il5"],
            "Financial Services": ["finance", "defi", "bank", "payment", "card", "transaction", "tax"],
            "Healthcare": ["health", "medical", "ehr", "clinical", "hospital", "patient"],
            "Hoch Family": ["hoch", "family", "household", "home lab"],
            "NorthStar Swarm OS": ["northstar", "swarm os", "swarm"],
            "Avionics & Aerospace Control": ["aerospace", "avionics", "space", "satellite"],
            "Biotech & Genomics": ["biotech", "gene", "protein", "dna", "genomic", "uniprot"]
        }
        
        self.phases = {
            "Active Incident Response": ["incident", "contain", "triage", "containment"],
            "Pre-Release Verification": ["cicd", "pre-release", "gate", "verify", "test", "build"],
            "Continuous Monitoring": ["monitoring", "conmon", "heartbeat", "log", "splunk"],
            "Operational Audit": ["audit", "comply", "report", "compliance"],
            "Initial Design": ["design", "threat model", "architecture"],
            "Recovery": ["recovery", "restore", "postmortem", "backup"],
            "Family Operations": ["family", "home", "personal"]
        }
        
        self.roles = {
            "Commander": ["commander", "lead", "triage", "incident"],
            "Evidence Collector": ["forensic", "evidence", "collect", "capture", "ledger"],
            "Auditor": ["audit", "compliance", "verify", "check"],
            "Remediator": ["remediate", "fix", "patch", "write", "change"],
            "Gatekeeper": ["gate", "approval", "policy"],
            "Monitor": ["monitor", "watchdog", "heartbeat"]
        }

    def classify(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        task = task_data.get("task", "")
        context = task_data.get("context", "")
        industry_req = task_data.get("industry")
        action_req = task_data.get("requested_action")
        
        combined_text = f"{task} {context} {industry_req or ''} {action_req or ''}".lower()
        
        # 1. Determine Domain
        selected_domain = "Cybersecurity"
        domain_scores = {}
        for dom, keywords in self.domains.items():
            score = sum(1 for kw in keywords if kw in combined_text)
            if score > 0:
                domain_scores[dom] = score
        if domain_scores:
            selected_domain = max(domain_scores, key=domain_scores.get)
            
        # 2. Determine Industry
        selected_industry = "All Industries"
        if industry_req and industry_req != "Auto Detect" and industry_req != "":
            selected_industry = industry_req
        else:
            ind_scores = {}
            for ind, keywords in self.industries.items():
                score = sum(1 for kw in keywords if kw in combined_text)
                if score > 0:
                    ind_scores[ind] = score
            if ind_scores:
                selected_industry = max(ind_scores, key=ind_scores.get)
                
        # 3. Determine Phase
        selected_phase = "Build"
        phase_scores = {}
        for ph, keywords in self.phases.items():
            score = sum(1 for kw in keywords if kw in combined_text)
            if score > 0:
                phase_scores[ph] = score
        if phase_scores:
            selected_phase = max(phase_scores, key=phase_scores.get)
            
        # 4. Determine Role
        selected_role = "Builder"
        role_scores = {}
        for rl, keywords in self.roles.items():
            score = sum(1 for kw in keywords if kw in combined_text)
            if score > 0:
                role_scores[rl] = score
        if role_scores:
            selected_role = max(role_scores, key=role_scores.get)
            
        # 5. Determine Risk Level
        risk_level = "LOW"
        high_risk_words = ["delete", "destroy", "deploy", "production", "credential", "firewall", "quarantine", "sandbox", "contain", "mitigate", "remediate", "admin"]
        medium_risk_words = ["privacy", "pii", "gdpr", "ccpa", "personal", "home", "family", "data classification"]
        
        if any(w in combined_text for w in high_risk_words) or selected_domain in ["Incident-Response", "Cloud-Security", "Infrastructure-Hardware", "Self-Healing"]:
            risk_level = "HIGH"
        elif any(w in combined_text for w in medium_risk_words) or selected_domain in ["Privacy", "Data-Security", "Family-Personal"]:
            risk_level = "MEDIUM"
            
        # 6. Confidence score
        matching_kws = sum(1 for keywords in list(self.domains.values()) + list(self.industries.values()) for kw in keywords if kw in combined_text)
        confidence = min(0.5 + (matching_kws * 0.1), 1.0)
        if not matching_kws:
            confidence = 0.5
            
        # 7. Reasoning summary
        reasoning = f"Classified task under '{selected_domain}' domain based on keyword matches. Assigned risk '{risk_level}'."
        
        return {
            "domain": selected_domain,
            "industry": selected_industry,
            "mission_phase": selected_phase,
            "runtime_role": selected_role,
            "risk_level": risk_level,
            "confidence": round(confidence, 2),
            "reasoning_summary": reasoning
        }
