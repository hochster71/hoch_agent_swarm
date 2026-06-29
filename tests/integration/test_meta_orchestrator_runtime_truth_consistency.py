import sqlite3
from fastapi.testclient import TestClient
from backend.main import app
from backend.runtime_truth.state_store import DB_PATH

client = TestClient(app)

def test_ownerless_domains_forces_high_orchestration_load():
    # Insert 39 ownerless domains in SQLite
    with sqlite3.connect(DB_PATH, timeout=60) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO runtime_truth_signals 
            (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence)
            VALUES ('ownerless_domain_count', 'Ownerless Domains Count', '39', 'test', 'test', '2026-06-29T12:00:00Z', 60, 'fresh', 1.0)
        """)
        conn.commit()

    # Re-collect to update michael_orchestration_load signal
    client.post("/api/v1/runtime-truth/collect")
    
    # Query state API to confirm it reads HIGH
    res = client.get("/api/v1/runtime-truth/state")
    assert res.status_code == 200
    data = res.json()
    
    load_sig = next(s for s in data["signals"] if s["signal_id"] == "michael_orchestration_load")
    assert load_sig["value"] == "HIGH"
