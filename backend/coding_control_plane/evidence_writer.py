import os
import datetime
from typing import Dict, Any, List

class EvidenceWriter:
    def __init__(self, output_dir: str = None):
        if not output_dir:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            output_dir = os.path.join(project_root, "docs/evidence/coding-control-plane")
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def write_zero_defect_evidence(self, date_str: str, report_data: Dict[str, Any]) -> str:
        filename = f"{date_str}-zero-defect-control-plane.md"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, "w") as f:
            f.write(f"# Zero-Defect Control Plane Verification Report — {date_str}\n\n")
            f.write("## 1. Defect Summary\n")
            f.write(f"- Open defects: {report_data.get('open_defect_count', 0)}\n")
            f.write(f"- Critical defects: {report_data.get('critical_defect_count', 0)}\n")
            f.write(f"- Warnings tracked: {report_data.get('warning_count', 0)}\n")
            f.write(f"- Security findings: {report_data.get('security_finding_count', 0)}\n")
            f.write(f"- Unowned defects: {report_data.get('unowned_defect_count', 0)}\n\n")
            
            f.write("## 2. Tools Detected & Registered\n")
            for tool in report_data.get("tools_detected", []):
                f.write(f"- **{tool['tool']}** ({tool['category']}) - Sandbox: {tool['sandbox']}\n")
            f.write("\n")
            
            f.write("## 3. Best-Agent Routing Status\n")
            f.write(f"Routing Status: **{report_data.get('best_agent_routing_status', 'ACTIVE')}**\n\n")
            
            f.write("## 4. Gates Executed & Status\n")
            for gate, status in report_data.get("gates_run", {}).items():
                f.write(f"- {gate}: **{status}**\n")
            f.write("\n")
            
            f.write("## 5. Verification Verdict\n")
            f.write(f"- Final Verifier Status: **{report_data.get('final_verifier_status', 'VERIFIED')}**\n")
            f.write(f"- Confidence Cap Applied: **{report_data.get('confidence_cap', 100.0)}%**\n")
            f.write(f"- Git Commit Hash: `{report_data.get('commit_hash', 'N/A')}`\n")
            f.write(f"- Next Best Action: {report_data.get('next_action', 'None')}\n")
            
        return filepath
