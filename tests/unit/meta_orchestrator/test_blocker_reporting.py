import sqlite3
from backend.runtime_truth.state_store import DB_PATH
from backend.runtime_truth.readiness_calculator import calculate_governed_readiness

def test_blockers_must_not_be_empty_with_critical_gaps():
    with sqlite3.connect(DB_PATH, timeout=60) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO runtime_truth_signals 
            (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence)
            VALUES ('critical_gap_count', 'Critical Gaps Count', '2', 'test', 'test', '2026-06-29T12:00:00Z', 60, 'fresh', 1.0)
        """)
        conn.commit()

    res = calculate_governed_readiness()
    assert len(res["caps"]) > 0
    assert any("critical gaps exist" in cap for cap in res["caps"])

def test_blockers_include_not_ready_autonomy_when_ownerless():
    with sqlite3.connect(DB_PATH, timeout=60) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO runtime_truth_signals 
            (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence)
            VALUES ('ownerless_domain_count', 'Ownerless Domains Count', '39', 'test', 'test', '2026-06-29T12:00:00Z', 60, 'fresh', 1.0)
        """)
        conn.commit()

    res = calculate_governed_readiness()
    assert any("business autonomy is NOT READY" in cap for cap in res["caps"])
