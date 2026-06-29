import os
import sqlite3
from backend.runtime_truth.state_store import DB_PATH
from backend.runtime_truth.readiness_calculator import calculate_governed_readiness

def test_critical_gaps_cap_readiness():
    # Insert mock critical gap count > 0 in DB
    with sqlite3.connect(DB_PATH, timeout=60) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO runtime_truth_signals 
            (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence)
            VALUES ('critical_gap_count', 'Critical Gaps Count', '1', 'test', 'test', '2026-06-29T12:00:00Z', 60, 'fresh', 1.0)
        """)
        conn.commit()

    res = calculate_governed_readiness()
    assert res["score"] <= 80.0
    assert "critical gaps exist" in res["caps"]

def test_missing_ui_container_caps_readiness():
    res = calculate_governed_readiness()
    assert res["score"] <= 80.0
