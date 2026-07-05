#!/usr/bin/env python3
import os
import sys
import json
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "has_live_project_tracker/data"
QUEUE_FILE = DATA_DIR / "helm_task_queue.json"
HEALTH_FILE = DATA_DIR / "ag_execution_queue_health.json"

def main():
    print("Executing AG Execution Queue Health Verification...")
    
    if not QUEUE_FILE.exists():
        print("❌ Verification failed: helm_task_queue.json does not exist.")
        sys.exit(1)
        
    with open(QUEUE_FILE, "r", encoding="utf-8") as f:
        queue = json.load(f)
        
    pending = 0
    completed = 0
    blocked = 0
    failed = 0
    
    task_ids = set()
    duplicate_ids = []
    stale_tasks = []
    
    now = datetime.datetime.now(datetime.timezone.utc)
    
    for task in queue:
        t_id = task.get("task_id")
        # Handle formats where key might be id instead
        if not t_id:
            t_id = task.get("id")
            
        if t_id:
            if t_id in task_ids:
                duplicate_ids.append(t_id)
            task_ids.add(t_id)
            
        status = task.get("status", "").lower()
        if status in ["pending", "queued", "retry_pending"]:
            pending += 1
            # Check staleness (if task has created_at timestamp)
            created_at_str = task.get("created_at")
            if created_at_str:
                try:
                    # Clean Z representation
                    ts = created_at_str.rstrip("Z").split("+")[0]
                    created_dt = datetime.datetime.fromisoformat(ts).replace(tzinfo=datetime.timezone.utc)
                    age_hours = (now - created_dt).total_seconds() / 3600.0
                    if age_hours > 24:
                        stale_tasks.append(t_id)
                except Exception:
                    pass
        elif status == "completed":
            completed += 1
        elif status == "blocked":
            blocked += 1
        elif status == "failed":
            failed += 1
            
    has_error = len(duplicate_ids) > 0
    health_status = "FAIL" if has_error else "PASS"
    
    health_payload = {
        "pending_count": pending,
        "completed_count": completed,
        "blocked_count": blocked,
        "failed_count": failed,
        "duplicate_ids": duplicate_ids,
        "stale_pending_tasks": stale_tasks,
        "health_status": health_status
    }
    
    with open(HEALTH_FILE, "w", encoding="utf-8") as f:
        json.dump(health_payload, f, indent=2)
        
    if has_error:
        print(f"❌ Queue validation failed. Duplicates detected: {duplicate_ids}")
        sys.exit(1)
        
    print(f"🟢 Queue Health verified successfully. Status: {health_status} (Pending: {pending}, Completed: {completed}, Blocked: {blocked}, Failed: {failed})")
    print("✅ AG Execution Queue verification PASSED.")
    sys.exit(0)

if __name__ == "__main__":
    main()
