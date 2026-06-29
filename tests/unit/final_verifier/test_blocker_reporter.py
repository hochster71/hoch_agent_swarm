import sqlite3
import pytest
from backend.runtime_truth.state_store import DB_PATH
from backend.final_verifier.blocker_reporter import BlockerReporter

def test_blocker_reporter_summarizes_gaps():
    with sqlite3.connect(DB_PATH, timeout=60) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO runtime_truth_signals
            (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence)
            VALUES ('critical_gap_count', 'Gaps', '3', 'test', 'test', '2026-06-29T12:00:00Z', 60, 'fresh', 1.0)
        """)
        conn.commit()

    reporter = BlockerReporter(db_path=DB_PATH)
    res = reporter.get_active_blockers()
    assert res["status"] == "success"
    assert res["blocker_count"] > 0
    assert any(b["type"] == "CRITICAL_GAP" for b in res["blockers"])

    # Clean up
    with sqlite3.connect(DB_PATH, timeout=60) as conn:
        conn.execute("DELETE FROM runtime_truth_signals WHERE signal_id = 'critical_gap_count'")
        conn.commit()
