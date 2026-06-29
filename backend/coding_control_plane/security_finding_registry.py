import sqlite3
import datetime
from typing import Dict, Any, List
from backend.runtime_truth.state_store import DB_PATH

class SecurityFindingRegistry:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path, timeout=60) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS security_findings (
                        finding_id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        file_path TEXT,
                        line_number INTEGER,
                        description TEXT,
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                """)
                conn.commit()
        except Exception:
            pass

    def record_finding(self, finding_id: str, title: str, severity: str, file_path: str, line_number: int, description: str) -> Dict[str, Any]:
        created_at = datetime.datetime.now(datetime.UTC).isoformat()
        try:
            with sqlite3.connect(self.db_path, timeout=60) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO security_findings
                    (finding_id, title, severity, file_path, line_number, description, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'OPEN', ?)
                """, (finding_id, title, severity, file_path, line_number, description, created_at))
                conn.commit()
            return {
                "finding_id": finding_id,
                "title": title,
                "severity": severity,
                "file_path": file_path,
                "line_number": line_number,
                "description": description,
                "status": "OPEN",
                "created_at": created_at
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_open_findings(self) -> List[Dict[str, Any]]:
        try:
            with sqlite3.connect(self.db_path, timeout=60) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM security_findings WHERE status = 'OPEN'")
                return [dict(row) for row in cursor.fetchall()]
        except Exception:
            return []
