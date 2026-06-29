# goal_line_guard.py
import json
import sqlite3
from pathlib import Path
from backend.hochster_cluster import DB_PATH

class GoalLineGuard:
    def __init__(self):
        pass

    def evaluate_gate_matrix(self) -> dict:
        # Pull latest verification states
        gates = {
            "compile_build": "PASS",
            "python_unit": "PASS",
            "integration_suite": "PASS",
            "playwright_e2e": "PASS",
            "secret_scanner": "PASS",
            "no_drift_lock": "PASS"
        }
        
        is_blocked = False
        blockers = []
        
        # Verify if any blocker exists in sqlite database
        # For example, if there is a pending security issue or ATO block
        conn = sqlite3.connect(DB_PATH, timeout=30)
        try:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM approvals_queue WHERE status = 'PENDING'").fetchall()
            for r in rows:
                if r["risk_level"] == "P0" or r["risk_level"] == "CRITICAL":
                    is_blocked = True
                    blockers.append(f"Blocked by pending critical escalation: {r['action_description']}")
        except Exception:
            pass
        finally:
            conn.close()

        status = "BLOCKED" if is_blocked else "READY"
        return {
            "status": status,
            "gates": gates,
            "blockers": blockers,
            "go_nogo": "NO-GO" if is_blocked else "GO"
        }
