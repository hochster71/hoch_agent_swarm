import sqlite3
from fastapi.testclient import TestClient
from backend.main import app
from backend.runtime_truth.state_store import DB_PATH

client = TestClient(app)

def test_final_verifier_integration_flow():
    # Insert contradicting signals into database
    with sqlite3.connect(DB_PATH, timeout=60) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO runtime_truth_signals
            (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence)
            VALUES ('production_go_status', 'Go Status', 'GO', 'test', 'test', '2026-06-29T12:00:00Z', 60, 'fresh', 1.0)
        """)
        conn.execute("""
            INSERT OR REPLACE INTO runtime_truth_signals
            (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence)
            VALUES ('production_nogo_status', 'NoGo Status', 'NO-GO', 'test', 'test', '2026-06-29T12:00:00Z', 60, 'fresh', 1.0)
        """)
        conn.commit()

    # Re-collect
    client.post("/api/v1/runtime-truth/collect")
    
    res = client.get("/api/v1/runtime-truth/state")
    assert res.status_code == 200
    data = res.json()

    # Check that final verifier status is BLOCKED due to contradiction
    verdict_sig = next(s for s in data["signals"] if s["signal_id"] == "final_verifier_status")
    assert verdict_sig["value"] == "BLOCKED"

    # Clean up
    with sqlite3.connect(DB_PATH, timeout=60) as conn:
        conn.execute("DELETE FROM runtime_truth_signals WHERE signal_id IN ('production_go_status', 'production_nogo_status')")
        conn.commit()

    # Restore passing state
    client.post("/api/v1/runtime-truth/collect")
