"""HELM ↔ AG IDE Relay Bridge.

Provides correlation ID generation, workspace/commit binding, and result/diff ingestion.
"""
from __future__ import annotations
import os
import json
import sqlite3
import datetime
import hashlib
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

class AGIDERelay:
    def __init__(self, repo_root: Path = PROJECT_ROOT):
        self.repo_root = repo_root
        self.task_file = repo_root / "coordination" / "ag_ide_tasks.json"

    def get_current_commit(self) -> str:
        try:
            return subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=str(self.repo_root),
                text=True,
                timeout=5
            ).strip()
        except Exception:
            return "UNKNOWN_COMMIT"

    def get_git_diff(self) -> str:
        try:
            return subprocess.check_output(
                ["git", "diff"],
                cwd=str(self.repo_root),
                text=True,
                timeout=5
            )
        except Exception:
            return ""

    def stage_task(self, task_id: str, prompt: str, scope: str) -> str:
        correlation_id = f"CR-{hashlib.sha256(task_id.encode()).hexdigest()[:8].upper()}"
        commit = self.get_current_commit()
        
        task_data = {
            "task_id": task_id,
            "correlation_id": correlation_id,
            "prompt": prompt,
            "scope": scope,
            "workspace_path": str(self.repo_root),
            "commit_bound": commit,
            "staged_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "status": "STAGED",
            "diff_before": self.get_git_diff()
        }
        
        # Save to coordination files
        tasks = []
        if self.task_file.exists():
            try:
                tasks = json.loads(self.task_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        
        # Avoid duplicate
        tasks = [t for t in tasks if t["task_id"] != task_id]
        tasks.append(task_data)
        
        self.task_file.parent.mkdir(parents=True, exist_ok=True)
        self.task_file.write_text(json.dumps(tasks, indent=2), encoding="utf-8")
        return correlation_id

    def complete_task(self, task_id: str, output: str, cmd_logs: List[str]) -> Dict[str, Any]:
        tasks = []
        if self.task_file.exists():
            try:
                tasks = json.loads(self.task_file.read_text(encoding="utf-8"))
            except Exception:
                pass
                
        target_task = None
        for t in tasks:
            if t["task_id"] == task_id:
                target_task = t
                break
                
        if not target_task:
            raise ValueError(f"Task {task_id} was not staged in AG IDE Relay")
            
        target_task["status"] = "COMPLETED"
        target_task["completed_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        target_task["output"] = output
        target_task["cmd_logs"] = cmd_logs
        target_task["diff_after"] = self.get_git_diff()
        target_task["commit_completed"] = self.get_current_commit()
        
        self.task_file.write_text(json.dumps(tasks, indent=2), encoding="utf-8")
        return target_task
