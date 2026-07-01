import sqlite3
import os
import json
from typing import Dict, Any, List
from backend.runtime_truth.state_store import DB_PATH

class AgentScoreboard:
    def __init__(self, db_path: str = str(DB_PATH)):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_scoreboard (
                agent_name TEXT,
                task_type TEXT,
                pass_rate REAL NOT NULL,
                diagnose_rate REAL DEFAULT 0.0,
                fix_rate REAL DEFAULT 0.0,
                regression_rate REAL DEFAULT 0.0,
                rejection_rate REAL DEFAULT 0.0,
                time_to_fix_seconds REAL DEFAULT 0.0,
                PRIMARY KEY (agent_name, task_type)
            )
        """)
        conn.commit()
        # Seed scoreboard with initial baseline scores
        initial_seed = [
            ("Claude Code", "frontend UI fix", 95.0, 92.0, 94.0, 1.0, 2.0, 120.0),
            ("Cursor", "frontend UI fix", 85.0, 80.0, 84.0, 3.0, 5.0, 180.0),
            ("Claude Code", "backend API fix", 98.0, 96.0, 97.0, 0.5, 1.0, 90.0),
            ("Codex CLI", "backend API fix", 90.0, 88.0, 89.0, 2.0, 4.0, 150.0),
            ("Semgrep Agent", "security patch", 99.0, 98.0, 98.5, 0.1, 0.5, 60.0),
            ("Claude Code", "security patch", 92.0, 90.0, 91.0, 1.5, 3.0, 140.0),
            ("Dependency Agent", "dependency fix", 99.5, 99.0, 99.2, 0.0, 0.1, 45.0),
            ("Documentation Agent", "doc generation", 97.5, 95.0, 97.0, 0.0, 0.5, 120.0),
            ("Architect Agent", "refactor", 96.0, 94.0, 95.0, 0.8, 1.2, 300.0)
        ]
        for row in initial_seed:
            conn.execute("""
                INSERT OR IGNORE INTO agent_scoreboard 
                (agent_name, task_type, pass_rate, diagnose_rate, fix_rate, regression_rate, rejection_rate, time_to_fix_seconds)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, row)
        conn.commit()
        conn.close()

    def get_best_agent(self, task_type: str) -> str:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT agent_name FROM agent_scoreboard WHERE task_type = ? ORDER BY pass_rate DESC LIMIT 1", (task_type,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else "Claude Code"

    def get_agent_scores(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT agent_name, task_type, pass_rate, diagnose_rate, fix_rate, regression_rate, rejection_rate, time_to_fix_seconds FROM agent_scoreboard")
        rows = cursor.fetchall()
        conn.close()
        
        scores = []
        for r in rows:
            scores.append({
                "agent_name": r[0],
                "task_type": r[1],
                "pass_rate": r[2],
                "diagnose_rate": r[3],
                "fix_rate": r[4],
                "regression_rate": r[5],
                "rejection_rate": r[6],
                "time_to_fix_seconds": r[7]
            })
        return scores
