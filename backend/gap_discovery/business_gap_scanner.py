import os
from typing import List, Dict, Any
from backend.gap_discovery.reference_models import REFERENCE_MODELS

class BusinessGapScanner:
    def __init__(self, project_root: str):
        self.project_root = project_root

    def scan(self) -> List[Dict[str, Any]]:
        gaps = []
        for target in REFERENCE_MODELS["business"]:
            full_path = os.path.join(self.project_root, target)
            if not os.path.exists(full_path):
                gaps.append({
                    "category": "business",
                    "target": target,
                    "description": f"Missing business operating model artifact: {target}",
                    "severity": "CRITICAL"
                })
        return gaps
