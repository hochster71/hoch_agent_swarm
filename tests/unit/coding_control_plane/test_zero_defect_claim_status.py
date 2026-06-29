import sqlite3
import pytest
from backend.runtime_truth.state_store import DB_PATH
from backend.final_verifier.final_verdict import FinalVerdict

def test_zero_defect_claim_blocking():
    # Insert a critical warning into coding_defects database
    with sqlite3.connect(DB_PATH, timeout=60) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO coding_defects
            (defect_id, description, severity, domain, status, created_at)
            VALUES ('test_blocking_warn', 'DeprecationWarning: test warning message', 'HIGH', 'backend', 'OPEN', '2026-06-29T12:00:00Z')
        """)
        conn.commit()

    verdict = FinalVerdict()
    res = verdict.get_final_verdict()
    
    # Clean up immediately
    with sqlite3.connect(DB_PATH, timeout=60) as conn:
        conn.execute("DELETE FROM coding_defects WHERE defect_id = 'test_blocking_warn'")
        conn.commit()

    # The warning contains "deprecation", making it classified as "NEW_BLOCKING".
    # Therefore, zero defect claim status must block release.
    assert res["status"] == "BLOCKED"
