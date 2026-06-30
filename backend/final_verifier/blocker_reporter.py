import sqlite3
import os
from typing import Dict, Any, List
from backend.runtime_truth.state_store import DB_PATH

class BlockerReporter:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def get_active_blockers(self) -> Dict[str, Any]:
        blockers = []
        
        try:
            with sqlite3.connect(self.db_path, timeout=60) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # 1. Check critical gaps
                cursor.execute("SELECT signal_id, value FROM runtime_truth_signals WHERE signal_id = 'critical_gap_count'")
                row = cursor.fetchone()
                if row and int(row["value"]) > 0:
                    blockers.append({
                        "type": "CRITICAL_GAP",
                        "description": f"There are {row['value']} open critical gaps in the meta-orchestrator backlog."
                    })

                # 2. Check ownerless domains
                cursor.execute("SELECT signal_id, value FROM runtime_truth_signals WHERE signal_id = 'ownerless_domain_count'")
                row = cursor.fetchone()
                if row and int(row["value"]) > 0:
                    blockers.append({
                        "type": "OWNERLESS_DOMAIN",
                        "description": f"There are {row['value']} business domains without assigned owner agents."
                    })

                # 3. Check open defects
                cursor.execute("SELECT count(*) as cnt FROM coding_defects WHERE status = 'OPEN'")
                cnt = cursor.fetchone()["cnt"]
                if cnt > 0:
                    blockers.append({
                        "type": "OPEN_DEFECTS",
                        "description": f"There are {cnt} open defects in the coding registry."
                    })

                # 4. Check unowned defects
                cursor.execute("SELECT count(*) as cnt FROM coding_defects WHERE status = 'OPEN' AND (owner_agent IS NULL OR owner_agent = '')")
                cnt = cursor.fetchone()["cnt"]
                if cnt > 0:
                    blockers.append({
                        "type": "UNOWNED_DEFECTS",
                        "description": f"There are {cnt} open defects without an owner agent assigned."
                    })

                # 5. Check high/critical vulnerabilities
                try:
                    cursor.execute("SELECT count(*) as cnt FROM security_findings WHERE severity IN ('CRITICAL', 'HIGH') AND status = 'OPEN'")
                    cnt = cursor.fetchone()["cnt"]
                    if cnt > 0:
                        blockers.append({
                            "type": "SECURITY_FINDING",
                            "description": f"There are {cnt} open CRITICAL or HIGH security findings."
                        })
                except Exception:
                    pass

                try:
                    cursor.execute("SELECT signal_id, value FROM runtime_truth_signals WHERE signal_id IN ('warning_blocking_count', 'warning_unknown_count')")
                    for row in cursor.fetchall():
                        val = int(row["value"])
                        if val > 0:
                            blockers.append({
                                "type": "BLOCKING_WARNING",
                                "description": f"There are {val} unresolved {row['signal_id']} warnings blocking release."
                            })
                except Exception:
                    pass

                # 7. Check for NO_ACTIVE_RELEASE_GO blocker
                from backend.runtime_truth.go_nogo_manager import GoNoGoManager
                try:
                    manager = GoNoGoManager(db_path=self.db_path)
                    summary = manager.process_and_update()
                    if summary["contradiction_status"] == "INACTIVE" and summary["active_go_count"] == 0 and summary["release_go_source"] == "none":
                        blockers.append({
                            "type": "NO_ACTIVE_RELEASE_GO",
                            "description": "No valid release GO source is active."
                        })
                except Exception:
                    pass

        except Exception as e:
            return {"status": "error", "blockers": [{"type": "SYSTEM_ERROR", "description": str(e)}]}

        return {
            "status": "success",
            "blocker_count": len(blockers),
            "blockers": blockers
        }
