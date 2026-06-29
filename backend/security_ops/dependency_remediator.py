import subprocess
import os
from typing import Dict, Any

class DependencyRemediator:
    def __init__(self, workspace_path: str = None):
        if not workspace_path:
            workspace_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.workspace_path = workspace_path

    def remediate_dependency(self, package_name: str, secure_version: str) -> Dict[str, Any]:
        """Runs pip-audit / npm audit remediation or uv add update command."""
        success = False
        message = ""

        # For Python dependencies, run uv add
        res = subprocess.run(["uv", "add", f"{package_name}>={secure_version}"], cwd=self.workspace_path, capture_output=True, text=True)
        if res.returncode == 0:
            success = True
            message = f"Successfully updated package {package_name} to >= {secure_version} via uv add."
        else:
            message = f"Failed to upgrade package {package_name}: {res.stderr}"

        return {
            "status": "SUCCESS" if success else "FAILED",
            "message": message,
            "package_name": package_name,
            "version_applied": secure_version
        }
