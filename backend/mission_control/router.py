import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone
from backend.runtime_truth.state_store import DB_PATH, apply_pragmas, now_iso

POD_AGENT_MAP = {
    "business": "Monetization & Compliance Agent",
    "cyber": "Security Auditor Agent",
    "hasf": "HASF Pipeline Agent",
    "has": "Personal Life Agent",
    "hobby": "Research & Innovation Agent",
    "ops": "Live Tracker Runtime Agent",
    "family": "Live Tracker Runtime Agent"
}

def create_mission_task_graph(mission_id: str, target_pod: str) -> list:
    agent_name = POD_AGENT_MAP.get(target_pod, "Live Tracker Runtime Agent")
    now = now_iso()
    
    if target_pod == "business":
        return [
            {
                "task_id": f"{mission_id}-step-1",
                "mission_id": mission_id,
                "name": "Check Market Readiness",
                "assigned_agent": agent_name,
                "status": "PENDING",
                "step_index": 1,
                "dependencies": "",
                "created_at": now,
                "updated_at": now
            },
            {
                "task_id": f"{mission_id}-step-2",
                "mission_id": mission_id,
                "name": "Verify Pricing Matrix",
                "assigned_agent": agent_name,
                "status": "PENDING",
                "step_index": 2,
                "dependencies": f"{mission_id}-step-1",
                "created_at": now,
                "updated_at": now
            },
            {
                "task_id": f"{mission_id}-step-3",
                "mission_id": mission_id,
                "name": "Build Release PR",
                "assigned_agent": agent_name,
                "status": "PENDING",
                "step_index": 3,
                "dependencies": f"{mission_id}-step-2",
                "created_at": now,
                "updated_at": now
            },
            {
                "task_id": f"{mission_id}-step-4",
                "mission_id": mission_id,
                "name": "Gate Authority Compliance Signoff",
                "assigned_agent": agent_name,
                "status": "PENDING",
                "step_index": 4,
                "dependencies": f"{mission_id}-step-3",
                "created_at": now,
                "updated_at": now
            },
            {
                "task_id": f"{mission_id}-step-5",
                "mission_id": mission_id,
                "name": "Operator Final Approval Gate",
                "assigned_agent": "Human Operator",
                "status": "PENDING",
                "step_index": 5,
                "dependencies": f"{mission_id}-step-4",
                "created_at": now,
                "updated_at": now
            }
        ]
    else:
        # Default simple graph
        return [
            {
                "task_id": f"{mission_id}-step-1",
                "mission_id": mission_id,
                "name": "Verify Preflight Config",
                "assigned_agent": agent_name,
                "status": "PENDING",
                "step_index": 1,
                "dependencies": "",
                "created_at": now,
                "updated_at": now
            },
            {
                "task_id": f"{mission_id}-step-2",
                "mission_id": mission_id,
                "name": "Operator Final Approval Gate",
                "assigned_agent": "Human Operator",
                "status": "PENDING",
                "step_index": 2,
                "dependencies": f"{mission_id}-step-1",
                "created_at": now,
                "updated_at": now
            }
        ]

def register_mission_and_tasks(mission_id: str, name: str, target_pod: str, command: str) -> dict:
    now = now_iso()
    tasks = create_mission_task_graph(mission_id, target_pod)
    
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        # Insert mission
        conn.execute("""
            INSERT INTO mission_control_missions (mission_id, name, target_pod, command, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (mission_id, name, target_pod, command, "PENDING", now, now))
        
        # Insert tasks
        for task in tasks:
            conn.execute("""
                INSERT INTO mission_control_tasks (task_id, mission_id, name, assigned_agent, status, step_index, dependencies, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task["task_id"],
                task["mission_id"],
                task["name"],
                task["assigned_agent"],
                task["status"],
                task["step_index"],
                task["dependencies"],
                task["created_at"],
                task["updated_at"]
            ))
        conn.commit()
    finally:
        conn.close()

    return {
        "mission_id": mission_id,
        "name": name,
        "target_pod": target_pod,
        "command": command,
        "status": "PENDING",
        "tasks": tasks
    }
