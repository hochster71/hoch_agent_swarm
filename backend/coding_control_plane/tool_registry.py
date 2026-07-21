import os
import shutil
import subprocess
import datetime
from typing import Dict, Any, List

class ToolRegistry:
    def __init__(self, policy_path: str = None):
        if not policy_path:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            policy_path = os.path.join(project_root, "config/tool_registry.yaml")
        self.policy_path = policy_path

    def get_registered_tools(self) -> List[Dict[str, Any]]:
        baseline_tools = [
            {
                "tool": "pytest",
                "category": "Python test runner",
                "sandbox": "Low",
                "cmd": "pytest --version",
                "binary": "pytest"
            },
            {
                "tool": "playwright",
                "category": "E2E browser testing",
                "sandbox": "Medium",
                "cmd": "npx playwright --version",
                "binary": "npx"
            },
            {
                "tool": "npm build",
                "category": "Frontend compiler",
                "sandbox": "Low",
                "cmd": "npm run build -- -h",
                "binary": "npm"
            },
            {
                "tool": "eslint",
                "category": "JS/TS linter",
                "sandbox": "Low",
                "cmd": "npx eslint --version",
                "binary": "npx"
            },
            {
                "tool": "tsc",
                "category": "TypeScript compiler",
                "sandbox": "Low",
                "cmd": "npx tsc --version",
                "binary": "npx"
            },
            {
                "tool": "ruff",
                "category": "Python linter/formatter",
                "sandbox": "Low",
                "cmd": "ruff --version",
                "binary": "ruff"
            },
            {
                "tool": "mypy",
                "category": "Python type checker",
                "sandbox": "Low",
                "cmd": "mypy --version",
                "binary": "mypy"
            },
            {
                "tool": "gitleaks",
                "category": "Secrets audit scanner",
                "sandbox": "Low",
                "cmd": "gitleaks version",
                "binary": "gitleaks"
            },
            {
                "tool": "semgrep",
                "category": "SAST scanner",
                "sandbox": "Low",
                "cmd": "semgrep --version",
                "binary": "semgrep"
            },
            {
                "tool": "npm audit",
                "category": "JS dependency vulnerability check",
                "sandbox": "Low",
                "cmd": "npm audit --help",
                "binary": "npm"
            },
            {
                "tool": "pip-audit",
                "category": "Python dependency vulnerability check",
                "sandbox": "Low",
                "cmd": "pip-audit --version",
                "binary": "pip-audit"
            },
            {
                "tool": "osv-scanner",
                "category": "Open source vulnerability scanner",
                "sandbox": "Low",
                "cmd": "osv-scanner --version",
                "binary": "osv-scanner"
            },
            {
                "tool": "trivy",
                "category": "Container/filesystem scanner",
                "sandbox": "Low",
                "cmd": "trivy --version",
                "binary": "trivy"
            },
            {
                "tool": "CycloneDX SBOM",
                "category": "Software Bill of Materials compiler",
                "sandbox": "Low",
                "cmd": "cyclonedx-py --version",
                "binary": "cyclonedx-py"
            },
            {
                "tool": "pre-commit",
                "category": "Git pre-commit hooks runner",
                "sandbox": "Low",
                "cmd": "pre-commit --version",
                "binary": "pre-commit"
            },
            {
                "tool": "OpenSSF Scorecard",
                "category": "Repository health evaluator",
                "sandbox": "Low",
                "cmd": "scorecard --version",
                "binary": "scorecard"
            },
            {
                "tool": "Codex CLI",
                "category": "Local terminal coding agent",
                "sandbox": "High (sandbox required)",
                "cmd": "codex --version",
                "binary": "codex"
            },
            {
                "tool": "Claude Code",
                "category": "Autonomous multi-file coding agent",
                "sandbox": "High (sandbox required)",
                "cmd": "claude --version",
                "binary": "claude"
            },
            {
                "tool": "Cursor",
                "category": "IDE coding assistant",
                "sandbox": "High (sandbox required)",
                "cmd": "cursor --version",
                "binary": "cursor"
            },
            {
                "tool": "Aider",
                "category": "Git-diff coding loop assistant",
                "sandbox": "High (sandbox required)",
                "cmd": "aider --version",
                "binary": "aider"
            }
        ]

        verified_inventory = []
        for t in baseline_tools:
            name = t["tool"]
            binary_name = t["binary"]
            verify_cmd = t["cmd"]
            
            # Look up path
            path = shutil.which(binary_name) or ""
            installed = False
            version = "Unknown"
            
            if path:
                # Attempt to get version
                try:
                    res = subprocess.run(
                        verify_cmd.split(),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=1.5
                    )
                    if res.returncode == 0:
                        installed = True
                        version = res.stdout.strip().splitlines()[0] if res.stdout.strip() else "Verified"
                except Exception:
                    # Fallback to simple path existence
                    installed = True
                    version = "Detected Path Only"

            # Determine status
            # If path exists but version check failed, it could be 'unavailable' or 'configured_only'
            # For simulated tools (e.g. tools we mock or run inside test environment), we can support simulated status
            if installed:
                status = "installed"
            else:
                # If we explicitly configure it but it is missing
                status = "missing" if path else "configured_only"

            verified_inventory.append({
                "tool": name,
                "configured": True,
                "installed": installed,
                "executable_path": path,
                "version": version,
                "verification_command": verify_cmd,
                "last_verified": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
                "status": status,
                "category": t["category"],
                "sandbox": t["sandbox"]
            })

        return verified_inventory
