import os
import yaml
from typing import Dict, Any, List

class ToolRegistry:
    def __init__(self, policy_path: str = None):
        if not policy_path:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            policy_path = os.path.join(project_root, "config/tool_registry.yaml")
        self.policy_path = policy_path
        self.policy = self._load_policy()

    def _load_policy(self) -> Dict[str, Any]:
        if os.path.exists(self.policy_path):
            with open(self.policy_path, "r") as f:
                return yaml.safe_load(f) or {}
        return {}

    def get_registered_tools(self) -> List[Dict[str, Any]]:
        # Hardcoded default tools as a baseline mapping required list
        baseline_tools = [
            {"tool": "pytest", "category": "Python test runner", "sandbox": "Low"},
            {"tool": "playwright", "category": "E2E browser testing", "sandbox": "Medium"},
            {"tool": "npm build", "category": "Frontend compiler", "sandbox": "Low"},
            {"tool": "eslint", "category": "JS/TS linter", "sandbox": "Low"},
            {"tool": "tsc", "category": "TypeScript compiler", "sandbox": "Low"},
            {"tool": "ruff", "category": "Python linter/formatter", "sandbox": "Low"},
            {"tool": "mypy", "category": "Python type checker", "sandbox": "Low"},
            {"tool": "gitleaks", "category": "Secrets audit scanner", "sandbox": "Low"},
            {"tool": "semgrep", "category": "SAST scanner", "sandbox": "Low"},
            {"tool": "npm audit", "category": "JS dependency vulnerability check", "sandbox": "Low"},
            {"tool": "pip-audit", "category": "Python dependency vulnerability check", "sandbox": "Low"},
            {"tool": "osv-scanner", "category": "Open source vulnerability scanner", "sandbox": "Low"},
            {"tool": "trivy", "category": "Container/filesystem scanner", "sandbox": "Low"},
            {"tool": "CycloneDX SBOM", "category": "Software Bill of Materials compiler", "sandbox": "Low"},
            {"tool": "pre-commit", "category": "Git pre-commit hooks runner", "sandbox": "Low"},
            {"tool": "OpenSSF Scorecard", "category": "Repository health evaluator", "sandbox": "Low"},
            {"tool": "Codex CLI", "category": "Local terminal coding agent", "sandbox": "High (sandbox required)"},
            {"tool": "Claude Code", "category": "Autonomous multi-file coding agent", "sandbox": "High (sandbox required)"},
            {"tool": "Cursor", "category": "IDE coding assistant", "sandbox": "High (sandbox required)"},
            {"tool": "Aider", "category": "Git-diff coding loop assistant", "sandbox": "High (sandbox required)"}
        ]
        return baseline_tools
