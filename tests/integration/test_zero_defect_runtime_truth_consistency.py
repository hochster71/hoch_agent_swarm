import sqlite3
from fastapi.testclient import TestClient
from backend.main import app
from backend.runtime_truth.state_store import DB_PATH

client = TestClient(app)

def test_zero_defect_runtime_truth_consistency():
    res = client.post("/api/v1/runtime-truth/collect")
    assert res.status_code == 200
    
    state_res = client.get("/api/v1/runtime-truth/state")
    assert state_res.status_code == 200
    data = state_res.json()
    
    signals = {s["signal_id"]: s["value"] for s in data["signals"]}
    
    # Assert new warning count signals exist
    assert "warning_blocking_count" in signals
    assert "warning_baselined_count" in signals
    assert "warning_unknown_count" in signals

    # Assert new tool count signals exist
    assert "verified_tool_count" in signals
    assert "missing_tool_count" in signals
    assert "configured_only_tool_count" in signals

    # Assert zero defect claim status exists
    assert "zero_defect_claim_status" in signals
