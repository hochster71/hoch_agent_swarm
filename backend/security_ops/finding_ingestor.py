import sqlite3
import os
import json
from typing import Dict, Any, List
from backend.runtime_truth.state_store import DB_PATH

class FindingIngestor:
    def __init__(self, db_path: str = str(DB_PATH)):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS security_findings (
                finding_id TEXT PRIMARY KEY,
                source_tool TEXT NOT NULL,
                severity TEXT NOT NULL,
                file_path TEXT,
                line_number INTEGER,
                description TEXT NOT NULL,
                status TEXT NOT NULL,
                detected_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def ingest_finding(self, finding_id: str, source_tool: str, severity: str, file_path: str, line_number: int, description: str) -> Dict[str, Any]:
        import datetime
        detected_at = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO security_findings (finding_id, source_tool, severity, file_path, line_number, description, status, detected_at)
            VALUES (?, ?, ?, ?, ?, ?, 'OPEN', ?)
        """, (finding_id, source_tool, severity, file_path, line_number, description, detected_at))
        conn.commit()
        conn.close()
        return {
            "finding_id": finding_id,
            "source_tool": source_tool,
            "severity": severity,
            "file_path": file_path,
            "line_number": line_number,
            "description": description,
            "status": "OPEN",
            "detected_at": detected_at
        }

    def get_open_findings(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT finding_id, source_tool, severity, file_path, line_number, description, status, detected_at FROM security_findings WHERE status = 'OPEN'")
        rows = cursor.fetchall()
        conn.close()
        
        findings = []
        for r in rows:
            findings.append({
                "finding_id": r[0],
                "source_tool": r[1],
                "severity": r[2],
                "file_path": r[3],
                "line_number": r[4],
                "description": r[5],
                "status": r[6],
                "detected_at": r[7]
            })
        return findings
