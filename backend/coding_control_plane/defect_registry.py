import sqlite3
from typing import List, Dict, Any
from backend.runtime_truth.state_store import DB_PATH

class DefectRegistry:
    def __init__(self, db_path: str = str(DB_PATH)):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS coding_defects (
                defect_id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                severity TEXT NOT NULL,
                domain TEXT NOT NULL,
                file_path TEXT,
                owner_agent TEXT,
                status TEXT NOT NULL,
                fix_attempts INTEGER DEFAULT 0,
                evidence_path TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def register_defect(self, defect_id: str, description: str, severity: str, domain: str, file_path: str = None, owner_agent: str = None) -> Dict[str, Any]:
        import datetime
        conn = sqlite3.connect(self.db_path)
        created_at = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
        conn.execute("""
            INSERT OR REPLACE INTO coding_defects (defect_id, description, severity, domain, file_path, owner_agent, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'OPEN', ?)
        """, (defect_id, description, severity, domain, file_path, owner_agent, created_at))
        conn.commit()
        conn.close()
        return {
            "defect_id": defect_id,
            "description": description,
            "severity": severity,
            "domain": domain,
            "file_path": file_path,
            "owner_agent": owner_agent,
            "status": "OPEN",
            "created_at": created_at
        }

    def get_defects(self, status: str = None) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if status:
            cursor.execute("SELECT defect_id, description, severity, domain, file_path, owner_agent, status, fix_attempts, evidence_path, created_at FROM coding_defects WHERE status = ?", (status,))
        else:
            cursor.execute("SELECT defect_id, description, severity, domain, file_path, owner_agent, status, fix_attempts, evidence_path, created_at FROM coding_defects")
        rows = cursor.fetchall()
        conn.close()
        
        defects = []
        for r in rows:
            defects.append({
                "defect_id": r[0],
                "description": r[1],
                "severity": r[2],
                "domain": r[3],
                "file_path": r[4],
                "owner_agent": r[5],
                "status": r[6],
                "fix_attempts": r[7],
                "evidence_path": r[8],
                "created_at": r[9]
            })
        return defects

    def update_defect(self, defect_id: str, updates: Dict[str, Any]):
        if not updates:
            return
        conn = sqlite3.connect(self.db_path)
        fields = []
        values = []
        for k, v in updates.items():
            fields.append(f"{k} = ?")
            values.append(v)
        values.append(defect_id)
        query = f"UPDATE coding_defects SET {', '.join(fields)} WHERE defect_id = ?"
        conn.execute(query, tuple(values))
        conn.commit()
        conn.close()
