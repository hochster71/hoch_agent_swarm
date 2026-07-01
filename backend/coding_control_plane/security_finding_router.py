import os
from typing import Dict, Any

class SecurityFindingRouter:
    def __init__(self):
        pass

    def route_finding(self, finding_id: str, severity: str, file_path: str) -> Dict[str, Any]:
        # Simple routing logic: Critical/High maps to dependency remediator or sast remediator
        assigned_handler = "sast_remediator"
        if "lockfile" in finding_id or "upgrade" in finding_id.lower() or "dependency" in finding_id.lower():
            assigned_handler = "dependency_remediator"

        action = "BLOCK_RELEASE"
        if severity == "MEDIUM":
            action = "ASSIGN_PLAN"
        elif severity == "LOW":
            action = "TRACK_ONLY"

        return {
            "finding_id": finding_id,
            "severity": severity,
            "file_path": file_path,
            "assigned_handler": assigned_handler,
            "remediation_action": action
        }
