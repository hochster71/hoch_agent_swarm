import sqlite3
from typing import Dict, Any, List
from backend.runtime_truth.state_store import DB_PATH

class DefectZeroValidator:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def validate_defects(self) -> Dict[str, Any]:
        violations = []
        try:
            with sqlite3.connect(self.db_path, timeout=60) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Rule 1: No ownerless defects
                cursor.execute("SELECT defect_id, description FROM coding_defects WHERE status = 'OPEN' AND (owner_agent IS NULL OR owner_agent = '')")
                for row in cursor.fetchall():
                    violations.append(f"Ownerless defect: {row['defect_id']} - {row['description']}")

                # Rule 2: No new warnings without accepted risk
                # We can check coding_defects table for entries containing "warning" with OPEN status
                cursor.execute("SELECT defect_id, description FROM coding_defects WHERE status = 'OPEN' AND description LIKE '%warning%'")
                for row in cursor.fetchall():
                    # check if an accepted risk exists for this defect_id
                    cursor.execute("SELECT count(*) as cnt FROM accepted_risks WHERE defect_id = ?", (row['defect_id'],))
                    if cursor.fetchone()["cnt"] == 0:
                        violations.append(f"Unwaived warning defect: {row['defect_id']} - {row['description']}")

        except Exception as e:
            return {"is_valid": False, "violations": [f"DB error: {str(e)}"]}

        return {
            "is_valid": len(violations) == 0,
            "violations": violations
        }
