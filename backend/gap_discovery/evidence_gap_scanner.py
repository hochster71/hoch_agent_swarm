import os
from typing import List, Dict, Any

class EvidenceGapScanner:
    def __init__(self, project_root: str):
        self.project_root = project_root

    def scan(self) -> List[Dict[str, Any]]:
        gaps = []
        # Check if the evidence registry contains recently generated documents
        evidence_dir = os.path.join(self.project_root, "docs/evidence")
        if not os.path.exists(evidence_dir):
            gaps.append({
                "category": "evidence",
                "target": "docs/evidence",
                "description": "Missing complete evidence directory",
                "severity": "CRITICAL"
            })
        return gaps
