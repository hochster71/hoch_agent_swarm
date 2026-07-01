import sqlite3
from typing import List, Dict, Any

class DecisionQueue:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS decision_queue (
                decision_id TEXT PRIMARY KEY,
                title TEXT,
                description TEXT,
                domain_id TEXT,
                severity TEXT,
                status TEXT,
                created_at TEXT
            )
        """)
        conn.commit()
        conn.close()

    def add_decision(self, decision_id: str, title: str, description: str, domain_id: str, severity: str):
        import datetime
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO decision_queue (decision_id, title, description, domain_id, severity, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (decision_id, title, description, domain_id, severity, "PENDING", datetime.datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()

    def get_pending_decisions(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT decision_id, title, description, domain_id, severity, status, created_at FROM decision_queue WHERE status = 'PENDING'")
        rows = cursor.fetchall()
        conn.close()
        
        decisions = []
        for r in rows:
            decisions.append({
                "decision_id": r[0],
                "title": r[1],
                "description": r[2],
                "domain_id": r[3],
                "severity": r[4],
                "status": r[5],
                "created_at": r[6]
            })
        return decisions

    def resolve_decision(self, decision_id: str, resolution: str):
        conn = sqlite3.connect(self.db_path)
        conn.execute("UPDATE decision_queue SET status = ? WHERE decision_id = ?", ("RESOLVED", decision_id))
        conn.commit()
        conn.close()

    def compute_orchestration_load(self) -> float:
        # Load index is based on count of pending decisions
        pending = len(self.get_pending_decisions())
        # Fatigue index scales from 0 to 100 based on pending items
        return min(100.0, float(pending * 10.0))
