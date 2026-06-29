import os
from typing import Dict, Any, List

class UiTruthValidator:
    def __init__(self, frontend_dir: str = "frontend"):
        self.frontend_dir = frontend_dir

    def validate_ui_truth(self) -> Dict[str, Any]:
        violations = []
        index_path = os.path.join(self.frontend_dir, "index.html")
        app_path = os.path.join(self.frontend_dir, "app.js")

        if not os.path.exists(index_path):
            return {"is_valid": False, "violations": ["frontend/index.html does not exist"]}

        try:
            with open(index_path, "r") as f:
                index_content = f.read()
        except Exception as e:
            return {"is_valid": False, "violations": [f"Failed to read index.html: {str(e)}"]}

        # Check that we have the required UI containers
        if "view-meta-orchestrator" not in index_content:
            violations.append("Missing view-meta-orchestrator UI container in index.html")
        if "view-defect-zero" not in index_content:
            violations.append("Missing view-defect-zero UI container in index.html")

        # Verify that there are no hardcoded fake green claims
        # e.g., if a span contains a hardcoded status like "100% SECURE" or similar
        for line_no, line in enumerate(index_content.splitlines(), 1):
            if "100% secure" in line.lower() or "fully autonomous" in line.lower():
                violations.append(f"Hardcoded absolute claim in index.html line {line_no}: '{line.strip()}'")

        return {
            "is_valid": len(violations) == 0,
            "violations": violations
        }
