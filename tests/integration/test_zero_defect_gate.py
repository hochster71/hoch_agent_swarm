import sqlite3
from fastapi.testclient import TestClient
from backend.main import app
from backend.runtime_truth.state_store import DB_PATH

client = TestClient(app)

def test_zero_defect_gate_verifies_telemetry():
    # Insert mock defects in coding_defects
    with sqlite3.connect(DB_PATH, timeout=60) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS coding_defects (
                defect_id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                severity TEXT NOT NULL,
                domain TEXT NOT NULL,
                file_path TEXT,
                owner_agent TEXT,
                status TEXT NOT NULL,
                fix_attempts INTEGER DEFAULT 0,
                evidence_path TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            INSERT OR REPLACE INTO coding_defects (defect_id, description, severity, domain, status, created_at)
            VALUES ('test_defect_1', 'failing unit test', 'HIGH', 'backend', 'OPEN', '2026-06-29T12:00:00Z')
        """)
        conn.execute("""
            INSERT OR REPLACE INTO coding_defects (defect_id, description, severity, domain, status, created_at)
            VALUES ('test_defect_2', 'syntax error in core', 'CRITICAL', 'backend', 'OPEN', '2026-06-29T12:00:00Z')
        """)
        conn.commit()

    # Re-collect
    client.post("/api/v1/runtime-truth/collect")
    
    res = client.get("/api/v1/runtime-truth/state")
    assert res.status_code == 200
    data = res.json()
    
    defect_sig = next(s for s in data["signals"] if s["signal_id"] == "open_defect_count")
    assert defect_sig["value"] == "2"

    # Clean up the mock defects so we don't pollute the live DB
    with sqlite3.connect(DB_PATH, timeout=60) as conn:
        conn.execute("DELETE FROM coding_defects WHERE defect_id IN ('test_defect_1', 'test_defect_2')")
        conn.commit()

    # Run collection pass again to restore 0 defects state in truth signals
    client.post("/api/v1/runtime-truth/collect")
