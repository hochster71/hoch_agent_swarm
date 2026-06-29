import os
from typing import List, Dict, Any
from backend.gap_discovery.reference_models import REFERENCE_MODELS

class LifecycleGapScanner:
    def __init__(self, project_root: str):
        self.project_root = project_root

    def scan(self) -> List[Dict[str, Any]]:
        gaps = []
        # Check SDLC/DDLC expected files/directories
        for target in REFERENCE_MODELS["sdlc"] + REFERENCE_MODELS["ddlc"]:
            full_path = os.path.join(self.project_root, target)
            if not os.path.exists(full_path):
                gaps.append({
                    "category": "lifecycle",
                    "target": target,
                    "description": f"Missing expected SDLC/DDLC path: {target}",
                    "severity": "CRITICAL" if "docs/evidence" in target or "tests" in target else "MEDIUM"
                })
        return gaps
