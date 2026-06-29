import os
from typing import List, Dict, Any
from backend.gap_discovery.reference_models import REFERENCE_MODELS

class RiskGapScanner:
    def __init__(self, project_root: str):
        self.project_root = project_root

    def scan(self) -> List[Dict[str, Any]]:
        gaps = []
        for target in REFERENCE_MODELS["risk"]:
            full_path = os.path.join(self.project_root, target)
            if not os.path.exists(full_path):
                gaps.append({
                    "category": "risk",
                    "target": target,
                    "description": f"Missing critical legal or sanitizer audit record: {target}",
                    "severity": "CRITICAL"
                })
        return gaps
