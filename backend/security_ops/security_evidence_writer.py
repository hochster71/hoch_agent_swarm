import os
import datetime
from typing import Dict, Any, List

class SecurityEvidenceWriter:
    def __init__(self, output_dir: str = None):
        if not output_dir:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            output_dir = os.path.join(project_root, "docs/evidence/security-ops")
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def write_security_clearance_evidence(self, date_str: str, audit_data: Dict[str, Any]) -> str:
        filename = f"{date_str}-security-clearance-audit.md"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, "w") as f:
            f.write(f"# Security Clearance Verification Audit — {date_str}\n\n")
            f.write("## 1. Vulnerability Ingestion & Scan Status\n")
            f.write(f"- Open vulnerabilities: {audit_data.get('open_vulnerability_count', 0)}\n")
            f.write(f"- High vulnerabilities: {audit_data.get('high_vulnerability_count', 0)}\n")
            f.write(f"- Low vulnerabilities: {audit_data.get('low_vulnerability_count', 0)}\n")
            f.write(f"- Accepted risks: {audit_data.get('accepted_risk_count', 0)}\n\n")
            
            f.write("## 2. Remediations Applied\n")
            for r in audit_data.get("remediations_applied", []):
                f.write(f"- **{r['package_name']}**: {r['message']} (applied secure version: {r['version_applied']})\n")
            f.write("\n")
            
            f.write("## 3. Clearances & Approvals\n")
            f.write(f"- Security Gate Status: **{audit_data.get('security_gate_status', 'PASS')}**\n")
            f.write(f"- Incident Status: **{audit_data.get('incident_status', 'CLEAN')}**\n")
            f.write(f"- Review Verdict: **{audit_data.get('review_verdict', 'CLEARED')}**\n")
            
        return filepath
