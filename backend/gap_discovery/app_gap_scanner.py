import os
from typing import List, Dict, Any

class AppGapScanner:
    def __init__(self, project_root: str):
        self.project_root = project_root

    def scan(self) -> List[Dict[str, Any]]:
        gaps = []
        # Check if the main-content view file exists and is populated
        index_path = os.path.join(self.project_root, "frontend/index.html")
        if os.path.exists(index_path):
            with open(index_path, "r") as f:
                content = f.read()
                if "view-meta-orchestrator" not in content:
                    gaps.append({
                        "category": "app",
                        "target": "frontend/index.html",
                        "description": "Missing view container #view-meta-orchestrator in frontend index page",
                        "severity": "MEDIUM"
                    })
        return gaps
