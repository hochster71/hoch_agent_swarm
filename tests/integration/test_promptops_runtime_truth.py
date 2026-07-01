import sqlite3
import os
from backend.promptops.promptops_runtime_truth import update_promptops_telemetry, get_db_path

def test_promptops_runtime_truth():
    contract = {
        "mission_id": "MSN-TEST",
        "prompt_class": "DOCKER_RUNTIME"
    }
    score_result = {"score": 85.0}
    risk_result = {"risk_level": "LOW"}
    
    update_promptops_telemetry(contract, score_result, risk_result)
    
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM runtime_truth_signals").fetchall()
        signals = {r["signal_id"]: r["value"] for r in rows}
        
        assert signals["promptops_status"] == "ACTIVE"
        assert signals["prompt_score"] == "85.0"
        assert signals["prompt_fake_completion_risk"] == "LOW"
        assert signals["last_prompt_class"] == "DOCKER_RUNTIME"
        assert signals["last_prompt_contract_id"] == "MSN-TEST"
    finally:
        conn.close()
