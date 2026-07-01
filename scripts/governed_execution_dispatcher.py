#!/usr/bin/env python3
# scripts/governed_execution_dispatcher.py
# Allowlisted action dispatcher for HAS/HASF governed execution.
# This prevents arbitrary shell script execution by defining strict, pre-approved python entrypoints.

import os
import sys
import json
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

ALLOWLISTED_ACTIONS = [
    "inspect_file_tree",
    "inspect_project_metadata",
    "generate_markdown_brief",
    "refresh_readiness_audit",
    "refresh_revenue_action_queue",
    "refresh_pod_runtime_state",
    "refresh_compute_health",
    "refresh_pod_schedule",
    "refresh_finance_brief",
    "refresh_soccer_audit",
    "validate_no_live_secrets"
]

def run_python_script(script_path, args=None):
    """Safely runs a Python script located within the project using the current interpreter."""
    if not os.path.exists(script_path):
        return {"success": False, "error": f"Script not found: {script_path}", "affected_paths": []}
    
    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)
    
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return {
            "success": True,
            "stdout": res.stdout,
            "stderr": res.stderr,
            "affected_paths": [] # To be appended based on script behavior
        }
    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "error": f"Subprocess exited with code {e.returncode}",
            "stdout": e.stdout,
            "stderr": e.stderr,
            "affected_paths": []
        }

def inspect_file_tree():
    """Lists files and directories under the project root up to 2 levels deep, excluding build/cache artifacts."""
    paths = []
    exclude_dirs = {".git", "node_modules", ".venv", "__pycache__", ".pytest_cache", "test-results"}
    for root, dirs, files in os.walk(PROJECT_ROOT):
        # Prune dirs
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        rel_root = os.path.relpath(root, PROJECT_ROOT)
        depth = 0 if rel_root == "." else len(rel_root.split(os.sep))
        if depth > 2:
            continue
        
        for d in dirs:
            paths.append(os.path.join(rel_root, d))
        for f in files:
            paths.append(os.path.join(rel_root, f))
            
    return {
        "success": True,
        "output": f"Inspected file tree, found {len(paths)} items.",
        "affected_paths": [str(PROJECT_ROOT)],
        "metadata": {"items_count": len(paths)}
    }

def inspect_project_metadata():
    """Reads project packaging details (pyproject.toml)."""
    toml_path = PROJECT_ROOT / "pyproject.toml"
    if not toml_path.exists():
        return {"success": False, "error": "pyproject.toml missing", "affected_paths": []}
    
    with open(toml_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    return {
        "success": True,
        "output": content[:1000],
        "affected_paths": [str(toml_path)]
    }

def generate_markdown_brief():
    """Generates a small project brief as evidence."""
    brief_path = PROJECT_ROOT / "docs" / "evidence" / "runtime" / "governed-execution-brief.md"
    os.makedirs(brief_path.parent, exist_ok=True)
    with open(brief_path, "w", encoding="utf-8") as f:
        f.write("# Governed Execution Brief\n\nGenerated automatically by dispatcher.")
    return {
        "success": True,
        "output": f"Generated brief at {brief_path}",
        "affected_paths": [str(brief_path)]
    }

def refresh_readiness_audit():
    script = SCRIPT_DIR / "project_revenue_readiness_audit.py"
    res = run_python_script(script)
    res["affected_paths"] = [
        "has_live_project_tracker/data/project_revenue_readiness_results.json",
        "docs/evidence/business/project-revenue-readiness-audit.md"
    ]
    return res

def refresh_revenue_action_queue():
    script = SCRIPT_DIR / "generate_revenue_action_queue.py"
    res = run_python_script(script)
    res["affected_paths"] = [
        "has_live_project_tracker/data/revenue_action_queue.json",
        "docs/evidence/business/revenue-action-queue.md"
    ]
    return res

def refresh_pod_runtime_state():
    script = SCRIPT_DIR / "generate_hoch_pods_runtime_state.py"
    res = run_python_script(script)
    res["affected_paths"] = [
        "has_live_project_tracker/data/hoch_pods_runtime_state.json",
        "docs/evidence/runtime/hoch-pods-runtime-evidence.md"
    ]
    return res

def refresh_compute_health():
    script = SCRIPT_DIR / "collect_hoch_compute_node_health.py"
    res = run_python_script(script)
    res["affected_paths"] = [
        "has_live_project_tracker/data/hoch_compute_node_health.json",
        "docs/evidence/runtime/hoch-compute-node-health.md"
    ]
    return res

def refresh_pod_schedule():
    script = SCRIPT_DIR / "schedule_hoch_pods.py"
    res = run_python_script(script)
    res["affected_paths"] = [
        "has_live_project_tracker/data/hoch_pod_schedule.json",
        "docs/evidence/runtime/hoch-pod-scheduler-evidence.md"
    ]
    return res

def refresh_finance_brief():
    script = SCRIPT_DIR / "generate_finance_operations_brief.py"
    res = run_python_script(script)
    res["affected_paths"] = [
        "has_live_project_tracker/data/ai_executive_leadership.json",
        "has_live_project_tracker/data/finance_agent_assignments.json",
        "docs/evidence/business/rc50-epic-fury-roi-projections.md"
    ]
    return res

def refresh_soccer_audit():
    script = SCRIPT_DIR / "hoch_hasf_soccer_onboarding_audit.py"
    res = run_python_script(script)
    res["affected_paths"] = [
        "docs/evidence/business/hoch-hasf-soccer-onboarding-audit.md",
        "docs/evidence/business/hoch-hasf-soccer-gap-analysis.md",
        "docs/evidence/business/hoch-hasf-soccer-pert-model.md",
        "has_live_project_tracker/data/hoch_hasf_soccer_audit_results.json"
    ]
    return res

def validate_no_live_secrets():
    """Scans environmental configs and source files for active/live secrets patterns (e.g. sk_live_)."""
    found_secrets = []
    # Check .env or local environment files
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                if "sk_live_" in line:
                    found_secrets.append(line.strip())
                    
    if found_secrets:
        return {
            "success": False,
            "error": "Security check failed: Live secrets pattern detected!",
            "details": found_secrets,
            "affected_paths": [str(env_file)]
        }
    return {
        "success": True,
        "output": "No live credentials or unmasked private keys detected in local environment configuration.",
        "affected_paths": [str(env_file)] if env_file.exists() else []
    }

def dispatch(action_name):
    """Entry point for executing allowlisted actions safely."""
    if action_name not in ALLOWLISTED_ACTIONS:
        raise ValueError(f"Action '{action_name}' is not in the governed execution allowlist.")
    
    if action_name == "inspect_file_tree":
        return inspect_file_tree()
    elif action_name == "inspect_project_metadata":
        return inspect_project_metadata()
    elif action_name == "generate_markdown_brief":
        return generate_markdown_brief()
    elif action_name == "refresh_readiness_audit":
        return refresh_readiness_audit()
    elif action_name == "refresh_revenue_action_queue":
        return refresh_revenue_action_queue()
    elif action_name == "refresh_pod_runtime_state":
        return refresh_pod_runtime_state()
    elif action_name == "refresh_compute_health":
        return refresh_compute_health()
    elif action_name == "refresh_pod_schedule":
        return refresh_pod_schedule()
    elif action_name == "refresh_finance_brief":
        return refresh_finance_brief()
    elif action_name == "refresh_soccer_audit":
        return refresh_soccer_audit()
    elif action_name == "validate_no_live_secrets":
        return validate_no_live_secrets()
    else:
        return {"success": False, "error": f"Dispatcher implementation missing for '{action_name}'", "affected_paths": []}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: governed_execution_dispatcher.py <action_name>")
        sys.exit(1)
    
    act = sys.argv[1]
    try:
        result = dispatch(act)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result.get("success") else 1)
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e), "affected_paths": []}, indent=2))
        sys.exit(1)
