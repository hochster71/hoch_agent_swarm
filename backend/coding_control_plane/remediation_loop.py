import subprocess
import os
from typing import Dict, Any, List

class RemediationLoop:
    def __init__(self, workspace_path: str = None):
        if not workspace_path:
            workspace_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.workspace_path = workspace_path

    def run_safe_remediation(self, defect_type: str, file_path: str) -> Dict[str, Any]:
        """Runs lint autofix, formatting, or safe minor fixes, verifying with tests after."""
        abs_path = os.path.join(self.workspace_path, file_path)
        if not os.path.exists(abs_path):
            return {"status": "FAILED", "reason": f"File not found: {file_path}"}

        success = False
        message = ""

        if defect_type == "formatting":
            # Run ruff format
            res = subprocess.run(["uv", "run", "ruff", "format", file_path], cwd=self.workspace_path, capture_output=True, text=True)
            if res.returncode == 0:
                success = True
                message = "Formatted with ruff format."
            else:
                message = f"Ruff formatting failed: {res.stderr}"
        elif defect_type == "lint autofix":
            # Run ruff check --fix
            res = subprocess.run(["uv", "run", "ruff", "check", "--fix", file_path], cwd=self.workspace_path, capture_output=True, text=True)
            if res.returncode == 0:
                success = True
                message = "Lint issues autofixed with ruff."
            else:
                message = f"Ruff autofix failed: {res.stderr}"
        else:
            success = True
            message = "Remediation type not auto-fix eligible."

        if success:
            # Run focused pytest for regression
            test_res = subprocess.run(["uv", "run", "pytest", "-q"], cwd=self.workspace_path, capture_output=True, text=True)
            if test_res.returncode != 0:
                success = False
                message += " Post-remediation regression tests failed!"

        return {
            "status": "SUCCESS" if success else "FAILED",
            "message": message,
            "defect_type": defect_type,
            "target_file": file_path
        }
