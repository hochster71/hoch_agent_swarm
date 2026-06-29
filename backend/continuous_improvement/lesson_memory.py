import sqlite3
import json
from backend.runtime_truth.state_store import DB_PATH, now_iso, apply_pragmas

class LessonMemory:
    def __init__(self):
        pass
        
    def record_lesson(self, failure_hash: str, analysis: dict, resolution: str):
        conn = sqlite3.connect(DB_PATH, timeout=30)
        apply_pragmas(conn)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO incidents (incident_id, title, severity, status, owner_agent, start_time, affected_component, root_cause, remediation, evidence_ref, closed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                failure_hash,
                analysis["error_summary"],
                "HIGH",
                "evidence_written",
                "RootCauseAnalyst",
                analysis["timestamp"],
                analysis["suspect_component"],
                analysis["root_cause_guess"],
                resolution,
                "",
                now_iso()
            ))
            conn.commit()
        finally:
            conn.close()
            
    def get_lessons(self) -> list:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        apply_pragmas(conn)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute("SELECT * FROM incidents ORDER BY start_time DESC").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
