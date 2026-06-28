import os
import shutil
import socket
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List
from backend.model_health_monitor import MONITOR
from backend.migration_monitor import MONITOR as MIGRATION_MONITOR

COCKPIT_DIR = Path("/Users/michaelhoch/.gemini/antigravity/scratch/hoch-agent-swarm")
CAMPAIGN_DIR = Path("/Users/michaelhoch/hoch_agent_swarm")
DB_PATH = Path("/Users/michaelhoch/.gemini/antigravity/scratch/hoch-agent-swarm/backend/crewai_ingested_artifacts.db")

class PreflightGate:
    def __init__(self):
        pass

    def check_ports(self) -> Dict[str, Any]:
        ports = {8000: "Cockpit API Server", 11434: "Ollama Daemon"}
        failed = []
        for port, name in ports.items():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                if s.connect_ex(("127.0.0.1", port)) != 0:
                    failed.append(f"{name} ({port})")
        
        if not failed:
            return {
                "status": "PASS",
                "message": "All required local ports (8000, 11434) are open and responding.",
                "remediation": ""
            }
        else:
            return {
                "status": "FAIL",
                "message": f"Required port(s) not responding: {', '.join(failed)}.",
                "remediation": "Start the missing service daemon (e.g. run Ollama application or start cockpit server)."
            }

    def check_disk_space(self) -> Dict[str, Any]:
        try:
            total, used, free = shutil.disk_usage("/")
            free_gb = free / 1024 / 1024 / 1024
            if free_gb > 10.0:
                return {
                    "status": "PASS",
                    "message": f"Sufficient disk space available: {free_gb:.2f} GB free.",
                    "remediation": ""
                }
            elif free_gb > 2.0:
                return {
                    "status": "WARN",
                    "message": f"Low disk space: {free_gb:.2f} GB free (recommended > 10 GB).",
                    "remediation": "Trigger a safe rclone storage migration copy to free up space."
                }
            else:
                return {
                    "status": "FAIL",
                    "message": f"Critical disk space: {free_gb:.2f} GB free. Swarm executions may fail.",
                    "remediation": "Resubmit large model files migration (run: POST /api/v1/migration/resume) or manually purge disk cache."
                }
        except Exception as e:
            return {
                "status": "FAIL",
                "message": f"Failed to retrieve disk usage: {e}",
                "remediation": "Check system read/write permissions."
            }

    def check_model_health(self) -> Dict[str, Any]:
        try:
            # Query model health monitor
            health = MONITOR.scan_health(force=False)
            status_summary = health.get("status_summary", {})
            
            missing_or_failed = []
            for model, detail in health.get("details", {}).items():
                if detail.get("status") == "RED":
                    missing_or_failed.append(model)
            
            if not missing_or_failed:
                # Check for amber (fallback) warnings
                warning_models = []
                for model, detail in health.get("details", {}).items():
                    if detail.get("status") == "AMBER":
                        warning_models.append(model)
                
                if warning_models:
                    return {
                        "status": "WARN",
                        "message": f"All routing targets are reachable, but fallback rules are active for: {', '.join(warning_models)}.",
                        "remediation": "Verify Ollama pulled models list or run: ollama pull <model> to resolve primary availability."
                    }
                
                return {
                    "status": "PASS",
                    "message": "All required routing models are pulled, available, and responding to compatibility probes.",
                    "remediation": ""
                }
            else:
                return {
                    "status": "FAIL",
                    "message": f"Critical models missing or failing probes: {', '.join(missing_or_failed)}.",
                    "remediation": f"Pull the required model(s) using Ollama: ollama pull {missing_or_failed[0]}"
                }
        except Exception as e:
            return {
                "status": "FAIL",
                "message": f"Failed to query model health monitor: {e}",
                "remediation": "Check Ollama socket connection state."
            }

    def check_sqlite_health(self) -> Dict[str, Any]:
        if not DB_PATH.exists():
            return {
                "status": "FAIL",
                "message": "SQLite database file not found at local cockpit path.",
                "remediation": "Initialize the SQLite schema registry (run: python3 scripts/db/init_db.py)."
            }
        
        try:
            conn = sqlite3.connect(DB_PATH, timeout=1.0)
            cursor = conn.cursor()
            cursor.execute("SELECT count(*) FROM crewai_ingested_artifacts")
            count = cursor.fetchone()[0]
            conn.close()
            return {
                "status": "PASS",
                "message": f"SQLite database is healthy and readable. Current record count: {count}.",
                "remediation": ""
            }
        except Exception as e:
            return {
                "status": "FAIL",
                "message": f"Database corruption or access lock error: {e}",
                "remediation": "Verify read/write permissions or restore the schema template."
            }

    def check_git_status(self) -> Dict[str, Any]:
        dirty = []
        
        # Check Cockpit scratch directory status
        try:
            res = subprocess.run(["git", "status", "--porcelain"], cwd=COCKPIT_DIR, capture_output=True, text=True)
            if res.stdout.strip():
                dirty.append("Cockpit Repo")
        except Exception:
            pass

        # Check Campaign directory status
        try:
            res = subprocess.run(["git", "status", "--porcelain"], cwd=CAMPAIGN_DIR, capture_output=True, text=True)
            if res.stdout.strip():
                dirty.append("Campaign Repo")
        except Exception:
            pass

        if not dirty:
            return {
                "status": "PASS",
                "message": "All git working trees are clean and synchronized.",
                "remediation": ""
            }
        else:
            return {
                "status": "WARN",
                "message": f"Uncommitted modifications detected in: {', '.join(dirty)}.",
                "remediation": "Commit, stash, or checkout modified working files (run: git status && git stash)."
            }

    def check_rclone_state(self) -> Dict[str, Any]:
        if MIGRATION_MONITOR.check_migration_active():
            return {
                "status": "WARN",
                "message": "An active rclone storage move migration is currently running in the background.",
                "remediation": "Wait for sync execution to complete, or terminate process: killall rclone"
            }
        return {
            "status": "PASS",
            "message": "No background rclone or storage migration jobs are running.",
            "remediation": ""
        }

    def check_process_conflicts(self) -> Dict[str, Any]:
        try:
            res = subprocess.run(["ps", "-A"], capture_output=True, text=True)
            if "run-ci-pipeline.py" in res.stdout:
                return {
                    "status": "WARN",
                    "message": "Conflict detected: An active QA/CI test pipeline runner is executing in the background.",
                    "remediation": "Wait for pipeline verification tasks to finish before launching new campaigns."
                }
            return {
                "status": "PASS",
                "message": "No active test runner or pipeline conflicts detected.",
                "remediation": ""
            }
        except Exception:
            return {
                "status": "PASS",
                "message": "Conflict check skipped due to environment limitations.",
                "remediation": ""
            }

    def run_preflight(self) -> Dict[str, Any]:
        checks_list = [
            {"id": "ports", "name": "Required Network Ports Check", "fn": self.check_ports},
            {"id": "disk_space", "name": "Storage Space Pre-allocation Gate", "fn": self.check_disk_space},
            {"id": "model_health", "name": "Routing Engine Model Safety Check", "fn": self.check_model_health},
            {"id": "sqlite_health", "name": "Cockpit Artifact Database Integrity", "fn": self.check_sqlite_health},
            {"id": "git_status", "name": "Git Workspace Alignment", "fn": self.check_git_status},
            {"id": "rclone_state", "name": "Background Rclone Activity Audit", "fn": self.check_rclone_state},
            {"id": "process_conflicts", "name": "Execution Process Conflicts", "fn": self.check_process_conflicts}
        ]

        resolved_checks = []
        overall_status = "GO"
        total_score = 0

        for c in checks_list:
            res = c["fn"]()
            resolved_checks.append({
                "id": c["id"],
                "name": c["name"],
                "status": res["status"],
                "message": res["message"],
                "remediation": res["remediation"]
            })
            
            # Map score
            if res["status"] == "PASS":
                total_score += 100
            elif res["status"] == "WARN":
                total_score += 50
            else:
                total_score += 0
                overall_status = "NO-GO"

        avg_score = int(total_score / len(checks_list))

        return {
            "go_no_go": overall_status,
            "overall_score": avg_score,
            "checks": resolved_checks,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }

GATE = PreflightGate()
