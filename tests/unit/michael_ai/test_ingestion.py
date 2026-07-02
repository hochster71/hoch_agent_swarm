import pytest
import sqlite3
from backend.michael_ai.ingestion import ingest_michael_prompt, ingest_ag_run
from backend.michael_ai.store import get_db_conn

def test_prompt_ingestion_stores_record():
    raw_prompt = "I need warp speed on the Michael AI Model because I am drowning. Lock HOCH-200 relay evidence."
    result = ingest_michael_prompt("manual", raw_prompt)
    
    assert result["prompt_id"] is not None
    assert result["lane"] == "Michael AI Model / Operator Twin / Continuous Learning Layer"
    assert result["urgency"] == "high"
    assert result["sentiment"] == "frustrated"
    assert "HOCH-200" in result["goal"]
    
    # Check SQLite store
    conn = get_db_conn()
    try:
        row = conn.execute("SELECT * FROM michael_prompts WHERE id = ?", (result["prompt_id"],)).fetchone()
        assert row is not None
        assert row["raw_text"] == raw_prompt
        assert row["urgency"] == "high"
    finally:
        conn.close()

def test_ag_run_ingestion_extracts_commit_and_evidence():
    task_desc = "Verify VPS configuration on 50.116.41.183"
    run_result = "SUCCESS: committed config changes in hash 97ac6a287e01 and created evidence docs/evidence/vps/20260702-1557-hoch200-vps-verification.md"
    
    res = ingest_ag_run("GOAL Orchestrator", task_desc, "SUCCESS", run_result, "Verify VPS configuration")
    
    assert res["run_id"] is not None
    assert "97ac6a287e01" in res["commits"]
    assert "docs/evidence/vps/20260702-1557-hoch200-vps-verification.md" in res["evidence"]
    
    # Check SQLite store for decisions
    conn = get_db_conn()
    try:
        decision = conn.execute("SELECT * FROM michael_decisions WHERE commit_hash LIKE '%97ac6a287e01%'").fetchone()
        assert decision is not None
        assert "97ac6a287e01" in decision["commit_hash"]
    finally:
        conn.close()
