import sqlite3
import os
from pathlib import Path
from backend.runtime_truth.state_store import DB_PATH, apply_pragmas

def init_mission_control_tables():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    apply_pragmas(conn)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mission_control_missions (
                mission_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                target_pod TEXT NOT NULL,
                command TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                result TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mission_control_tasks (
                task_id TEXT PRIMARY KEY,
                mission_id TEXT NOT NULL,
                name TEXT NOT NULL,
                assigned_agent TEXT,
                status TEXT NOT NULL,
                step_index INTEGER NOT NULL,
                dependencies TEXT,
                error_message TEXT,
                evidence_path TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()

# Auto-initialize
init_mission_control_tables()
