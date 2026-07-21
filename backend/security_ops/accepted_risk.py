import sqlite3
from typing import List, Dict, Any
from backend.runtime_truth.state_store import DB_PATH

class AcceptedRisk:
    def __init__(self, db_path: str = str(DB_PATH)):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS accepted_risks (
                risk_id TEXT PRIMARY KEY,
                defect_id TEXT NOT NULL,
                justification TEXT NOT NULL,
                operator_approval INTEGER NOT NULL,
                expiration_date TEXT,
                approved_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def record_accepted_risk(self, risk_id: str, defect_id: str, justification: str, expiration_date: str = None) -> Dict[str, Any]:
        import datetime
        ts = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO accepted_risks (risk_id, defect_id, justification, operator_approval, expiration_date, approved_at)
            VALUES (?, ?, ?, 1, ?, ?)
        """, (risk_id, defect_id, justification, expiration_date, ts))
        conn.commit()
        conn.close()
        return {
            "risk_id": risk_id,
            "defect_id": defect_id,
            "justification": justification,
            "operator_approval": 1,
            "expiration_date": expiration_date,
            "approved_at": ts
        }

    def get_accepted_risks(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT risk_id, defect_id, justification, operator_approval, expiration_date, approved_at FROM accepted_risks")
        rows = cursor.fetchall()
        conn.close()
        
        risks = []
        for r in rows:
            risks.append({
                "risk_id": r[0],
                "defect_id": r[1],
                "justification": r[2],
                "operator_approval": bool(r[3]),
                "expiration_date": r[4],
                "approved_at": r[5]
            })
        return risks
