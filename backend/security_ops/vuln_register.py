import sqlite3
from typing import List, Dict, Any
from backend.runtime_truth.state_store import DB_PATH

class VulnRegister:
    def __init__(self, db_path: str = str(DB_PATH)):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS security_vulns (
                vuln_id TEXT PRIMARY KEY,
                cve_id TEXT,
                package_name TEXT,
                severity TEXT NOT NULL,
                status TEXT NOT NULL,
                remediation_plan TEXT,
                last_updated TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def register_vuln(self, vuln_id: str, cve_id: str, package_name: str, severity: str, status: str = "OPEN") -> Dict[str, Any]:
        import datetime
        ts = datetime.datetime.now(datetime.UTC).isoformat() + "Z"
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO security_vulns (vuln_id, cve_id, package_name, severity, status, last_updated)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (vuln_id, cve_id, package_name, severity, status, ts))
        conn.commit()
        conn.close()
        return {
            "vuln_id": vuln_id,
            "cve_id": cve_id,
            "package_name": package_name,
            "severity": severity,
            "status": status,
            "last_updated": ts
        }

    def get_vulns(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT vuln_id, cve_id, package_name, severity, status, remediation_plan, last_updated FROM security_vulns")
        rows = cursor.fetchall()
        conn.close()
        
        vulns = []
        for r in rows:
            vulns.append({
                "vuln_id": r[0],
                "cve_id": r[1],
                "package_name": r[2],
                "severity": r[3],
                "status": r[4],
                "remediation_plan": r[5],
                "last_updated": r[6]
            })
        return vulns
