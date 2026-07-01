import sqlite3
import pytest
from backend.runtime_truth.state_store import DB_PATH
from backend.final_verifier.readiness_cap_engine import ReadinessCapEngine

def test_readiness_caps_applied():
    # Insert mock signals indicating critical gaps and ownerless domains
    with sqlite3.connect(DB_PATH, timeout=60) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO runtime_truth_signals
            (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence)
            VALUES ('critical_gap_count', 'Gaps', '1', 'test', 'test', '2026-06-29T12:00:00Z', 60, 'fresh', 1.0)
        """)
        conn.execute("""
            INSERT OR REPLACE INTO runtime_truth_signals
            (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence)
            VALUES ('ownerless_domain_count', 'Ownerless', '12', 'test', 'test', '2026-06-29T12:00:00Z', 60, 'fresh', 1.0)
        """)
        conn.commit()

    engine = ReadinessCapEngine(db_path=DB_PATH)
    res = engine.calculate_caps()
    assert res["score"] <= 50.0  # since ownerless domain caps at 50 (not_ready_cap)
    assert "critical gaps exist" in res["caps"]
    assert "business autonomy is NOT READY" in res["caps"]

    # Clean up
    with sqlite3.connect(DB_PATH, timeout=60) as conn:
        conn.execute("DELETE FROM runtime_truth_signals WHERE signal_id IN ('critical_gap_count', 'ownerless_domain_count')")
        conn.commit()
