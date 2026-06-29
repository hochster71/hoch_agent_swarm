import sqlite3
from typing import Dict, Any, List
from backend.runtime_truth.state_store import DB_PATH

class OwnerAssignmentManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def assign_defect_owner(self, defect_id: str, owner_agent: str) -> bool:
        try:
            with sqlite3.connect(self.db_path, timeout=60) as conn:
                conn.execute("""
                    UPDATE coding_defects
                    SET owner_agent = ?
                    WHERE defect_id = ?
                """, (owner_agent, defect_id))
                conn.commit()
                return True
        except Exception:
            return False

    def assign_domain_owner(self, domain_id: str, owner_agent: str) -> bool:
        try:
            with sqlite3.connect(self.db_path, timeout=60) as conn:
                conn.execute("""
                    UPDATE business_domains
                    SET owner_agent = ?
                    WHERE domain_id = ?
                """, (owner_agent, domain_id))
                conn.commit()
                return True
        except Exception:
            return False
