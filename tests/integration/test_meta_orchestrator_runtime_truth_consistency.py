import sqlite3
from fastapi.testclient import TestClient
from backend.main import app
from backend.runtime_truth.state_store import DB_PATH

client = TestClient(app)

def test_meta_orchestrator_runtime_truth_consistency():
    res = client.post("/api/v1/runtime-truth/collect")
    assert res.status_code == 200
    
    state_res = client.get("/api/v1/runtime-truth/state")
    assert state_res.status_code == 200
    data = state_res.json()
    assert "signals" in data
