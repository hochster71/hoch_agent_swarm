import sqlite3
import pytest
from backend.runtime_truth.state_store import DB_PATH
from backend.final_verifier.contradiction_checker import ContradictionChecker

def test_contradiction_checker_go_nogo_active():
    from backend.runtime_truth.state_store import now_iso
    now_str = now_iso()
    with sqlite3.connect(DB_PATH, timeout=60) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO runtime_truth_signals
            (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence)
            VALUES ('production_go_status', 'Go Status', 'GO', 'manual', 'user', ?, 60, 'fresh', 1.0)
        """, (now_str,))
        conn.execute("""
            INSERT OR REPLACE INTO runtime_truth_signals
            (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence)
            VALUES ('production_nogo_status', 'NoGo Status', 'NO-GO', 'computed', 'system', ?, 60, 'fresh', 1.0)
        """, (now_str,))
        conn.commit()

    checker = ContradictionChecker(db_path=DB_PATH)
    res = checker.check_contradictions()
    assert res["is_valid"] is False
    assert any("GO and NO-GO contradiction" in v for v in res["violations"])

    # Clean up
    with sqlite3.connect(DB_PATH, timeout=60) as conn:
        conn.execute("DELETE FROM runtime_truth_signals WHERE signal_id IN ('production_go_status', 'production_nogo_status')")
        conn.commit()
