import os
import json
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
import sys
sys.path.insert(0, str(PROJECT_ROOT))
DB_PATH = PROJECT_ROOT / "backend" / "swarm_ledger.db"
SCHEDULER_METRICS = PROJECT_ROOT / "has_live_project_tracker" / "data" / "scheduler_metrics.json"

# Worker Profiles defining heterogeneous capabilities and resources
WORKER_PROFILES = {
    "HAS-WORKER-RELAY-001": {
        "agent_name": "Relay Worker (hoch-relay-001)",
        "capabilities": ["networking", "relay", "proxy", "security", "verification"],
        "assigned_pods": ["cyber", "hasf"],
        "cores": 4,
        "memory_gb": 8.0,
        "type": "ARM64 VPS compute node"
    },
    "Live Tracker Runtime Agent": {
        "agent_name": "Live Tracker Runtime Agent",
        "capabilities": ["ops", "family", "status", "tracker", "general"],
        "assigned_pods": ["ops", "family"],
        "cores": 2,
        "memory_gb": 4.0,
        "type": "Local Primary compute node"
    },
    "Monetization & Compliance Agent": {
        "agent_name": "Monetization & Compliance Agent",
        "capabilities": ["business", "money", "billing", "stripe"],
        "assigned_pods": ["business"],
        "cores": 2,
        "memory_gb": 4.0,
        "type": "Secure sandbox compliance node"
    },
    "Security Auditor Agent": {
        "agent_name": "Security Auditor Agent",
        "capabilities": ["cyber", "security", "audit"],
        "assigned_pods": ["cyber"],
        "cores": 2,
        "memory_gb": 4.0,
        "type": "Isolated audit sandbox"
    },
    "Master Orchestrator": {
        "agent_name": "Master Orchestrator",
        "capabilities": ["orchestration", "general"],
        "assigned_pods": ["ops", "business"],
        "cores": 4,
        "memory_gb": 8.0,
        "type": "Coordinator control node"
    }
}

# Tasks prioritized if they belong to critical components
CRITICAL_PODS = ["cyber", "hasf", "ops"]

def now_iso():
    return datetime.now(timezone.utc).isoformat() + "Z"

def run_scheduler() -> dict:
    if not DB_PATH.exists():
        return {"status": "error", "message": "Database not found."}
        
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    
    try:
        # 1. Fetch all pending tasks
        pending_tasks = [dict(r) for r in conn.execute("""
            SELECT t.*, m.target_pod, m.name as mission_name 
            FROM mission_control_tasks t
            JOIN mission_control_missions m ON t.mission_id = m.mission_id
            WHERE t.status = 'PENDING'
            ORDER BY t.step_index ASC
        """).fetchall()]
        
        # 2. Fetch all completed task IDs to check dependencies
        completed_tasks = {r["task_id"] for r in conn.execute("""
            SELECT task_id FROM mission_control_tasks WHERE status = 'COMPLETED'
        """).fetchall()}
        
        # 3. Identify running tasks to see which workers are busy
        running_tasks = [dict(r) for r in conn.execute("""
            SELECT t.*, m.target_pod FROM mission_control_tasks t
            JOIN mission_control_missions m ON t.mission_id = m.mission_id
            WHERE t.status = 'RUNNING'
        """).fetchall()]
        
        busy_agents = {t["assigned_agent"] for t in running_tasks}
        
        # Determine runnable tasks (all dependencies met)
        runnable = []
        for t in pending_tasks:
            dep_str = t.get("dependencies", "")
            deps = [d.strip() for d in dep_str.split(",") if d.strip()]
            if all(d in completed_tasks for d in deps):
                runnable.append(t)
                
        # Prioritize runnable tasks (critical pod tasks first)
        runnable.sort(key=lambda x: 0 if x["target_pod"] in CRITICAL_PODS else 1)
        
        scheduled_tasks = []
        allocated_cores = sum(WORKER_PROFILES.get(t["assigned_agent"], {}).get("cores", 2) for t in running_tasks)
        allocated_mem = sum(WORKER_PROFILES.get(t["assigned_agent"], {}).get("memory_gb", 4.0) for t in running_tasks)
        
        # 4. Schedule tasks
        for task in runnable:
            agent = task["assigned_agent"]
            
            # Map default or unassigned agent to a specific worker profile
            if not agent or agent == "Human Operator":
                continue # operator approval tasks wait for human interaction
                
            # If the agent worker is currently busy, skip to avoid overloading
            if agent in busy_agents:
                continue
                
            # Worker match profile check
            profile = WORKER_PROFILES.get(agent)
            if not profile:
                continue
                
            # Safe task auto-execution
            # (Epic fury tasks step 1 to 4 are low-risk automation-safe)
            is_high_risk = "step-5" in task["task_id"] or "approval" in task["name"].lower()
            
            if is_high_risk:
                # Mark as WAITING_FOR_APPROVAL in database, do not auto-run
                conn.execute("""
                    UPDATE mission_control_tasks SET status = 'WAITING_FOR_APPROVAL', updated_at = ? WHERE task_id = ?
                """, (now_iso(), task["task_id"]))
                continue
                
            # Execute safe action
            print(f"[SCHEDULER] Dispatching task {task['task_id']} ({task['name']}) to {agent} ({profile['type']})")
            
            # Map task name/role to a safe local validation job command
            cmd = ["bash", "scripts/local_compute_job_queue.sh"]
            if "Market" in task["name"]:
                cmd = ["bash", "scripts/rc34_usage_guardrail_verify.sh"]
            elif "Pricing" in task["name"]:
                cmd = ["bash", "scripts/rc32_automation_cadence_verify.sh"]
            elif "Release" in task["name"]:
                # Safe Playwright E2E spec execution
                cmd = ["npx", "playwright", "test", "tests/e2e/rc33-compute-utilization.spec.ts"]
            
            print(f"[SCHEDULER] Invoking command: {' '.join(cmd)}")
            res_proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT))
            
            status_val = "COMPLETED" if res_proc.returncode == 0 else "FAILED"
            evidence_file = f"artifacts/evidence/scheduler_{task['task_id']}.json"
            abs_evidence = PROJECT_ROOT / "has_live_project_tracker" / evidence_file
            os.makedirs(abs_evidence.parent, exist_ok=True)
            
            evidence_data = {
                "task_id": task["task_id"],
                "name": task["name"],
                "dispatched_worker": agent,
                "worker_type": profile["type"],
                "executed_at": now_iso(),
                "status": status_val,
                "cores_utilized": profile["cores"],
                "memory_utilized_gb": profile["memory_gb"],
                "command": cmd,
                "exit_code": res_proc.returncode,
                "stdout_snippet": res_proc.stdout[-500:] if res_proc.stdout else "",
                "stderr_snippet": res_proc.stderr[-500:] if res_proc.stderr else ""
            }
            with open(abs_evidence, "w") as f:
                json.dump(evidence_data, f, indent=2)
                
            # Update database status
            conn.execute("""
                UPDATE mission_control_tasks 
                SET status = ?, evidence_path = ?, updated_at = ? 
                WHERE task_id = ?
            """, (status_val, evidence_file, now_iso(), task["task_id"]))
            
            # If this is the compliance signoff (step 4), update mission to WAITING_FOR_APPROVAL
            if task["step_index"] == 4:
                conn.execute("""
                    UPDATE mission_control_missions 
                    SET status = 'WAITING_FOR_APPROVAL', updated_at = ? 
                    WHERE mission_id = ?
                """, (now_iso(), task["mission_id"]))
            else:
                conn.execute("""
                    UPDATE mission_control_missions 
                    SET status = 'RUNNING', updated_at = ? 
                    WHERE mission_id = ?
                """, (now_iso(), task["mission_id"]))
                
            scheduled_tasks.append(task["task_id"])
            busy_agents.add(agent)
            allocated_cores += profile["cores"]
            allocated_mem += profile["memory_gb"]
            
        conn.commit()
        
        # Calculate utilization stats
        total_workers = len(WORKER_PROFILES)
        active_workers_count = len(busy_agents)
        utilization_percent = round((active_workers_count / total_workers) * 100.0, 1)
        
        metrics = {
            "scheduler_state": "ACTIVE" if scheduled_tasks or active_workers_count > 0 else "IDLE",
            "utilization_percent": utilization_percent,
            "active_workers_count": active_workers_count,
            "total_workers_count": total_workers,
            "running_tasks_count": len(running_tasks) + len(scheduled_tasks),
            "completed_tasks_count": len(completed_tasks) + len(scheduled_tasks),
            "cores_allocated": allocated_cores,
            "memory_allocated_gb": allocated_mem,
            "scheduled_this_cycle": scheduled_tasks,
            "timestamp": now_iso()
        }
        
        os.makedirs(SCHEDULER_METRICS.parent, exist_ok=True)
        with open(SCHEDULER_METRICS, "w") as f:
            json.dump(metrics, f, indent=2)
            
        return metrics
        
    finally:
        conn.close()

if __name__ == "__main__":
    res = run_scheduler()
    print(json.dumps(res, indent=2))
