import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.prompt_registry import get_registry
from pathlib import Path
import json
import os
import shutil

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_teardown_ledger_file():
    # Setup: ensure promptops store and evidenceops ledger are initialized
    base_dir = Path(__file__).resolve().parent.parent
    ledger_path = base_dir / "data" / "prompt_registry" / "evidenceops_ledger.json"
    backup_path = base_dir / "data" / "prompt_registry" / "evidenceops_ledger.json.bak"
    
    # Backup existing ledger if it exists
    if ledger_path.exists():
        shutil.copy(ledger_path, backup_path)
        ledger_path.unlink()
        
    yield
    
    # Teardown: restore backup ledger
    if ledger_path.exists():
        ledger_path.unlink()
    if backup_path.exists():
        shutil.copy(backup_path, ledger_path)
        backup_path.unlink()

def test_evidenceops_endpoints_exist_and_fetch():
    # 1. Fetch metrics
    response_metrics = client.get("/api/evidenceops/metrics")
    assert response_metrics.status_code == 200
    data = response_metrics.json()
    assert "total_runs" in data
    assert "approval_events" in data
    assert "fixture_drift" in data
    assert "quarantined_prompts" in data
    assert "stale_prompts" in data

    # 2. Fetch daily snapshot
    response_snap = client.get("/api/evidenceops/daily-snapshot")
    assert response_snap.status_code == 200
    snap_data = response_snap.json()
    assert "active_prompts_count" in snap_data
    assert "failed_fixtures_count" in snap_data
    assert "hash_drift_count" in snap_data
    assert "stale_review_items_count" in snap_data

    # 3. Fetch runs (should be empty initially)
    response_runs = client.get("/api/evidenceops/runs")
    assert response_runs.status_code == 200
    assert isinstance(response_runs.json(), list)

def test_run_prompt_logs_to_ledger():
    # Choose a low risk prompt to run
    prompt_id = "QA-002"
    
    response_run = client.post(f"/api/prompts/{prompt_id}/run")
    assert response_run.status_code in [200, 500] # Swarm might fail on local model missing, but endpoint should try execution
    
    # Verify that ledger now has at least one run entry
    runs_res = client.get("/api/evidenceops/runs")
    assert runs_res.status_code == 200
    runs = runs_res.json()
    assert len(runs) >= 1
    
    latest_run = runs[-1]
    assert latest_run["prompt_id"] == prompt_id
    assert "verdict" in latest_run
    assert "run_id" in latest_run
    
    # Test details lookup by run_id
    run_id = latest_run["run_id"]
    res_detail = client.get(f"/api/evidenceops/runs/{run_id}")
    assert res_detail.status_code == 200
    assert res_detail.json()["run_id"] == run_id

def test_export_evidence_bundle():
    # Make a run to log history
    client.post("/api/prompts/QA-002/run")
    
    # Export bundle
    res_export = client.post("/api/evidenceops/export")
    assert res_export.status_code == 200
    files = res_export.json()["files"]
    assert "markdown" in files
    assert "json" in files
    assert "csv" in files
    assert "zip" in files
    
    base_dir = Path(__file__).resolve().parent.parent
    assert (base_dir / files["markdown"]).exists()
    assert (base_dir / files["json"]).exists()
    assert (base_dir / files["csv"]).exists()
    assert (base_dir / files["zip"]).exists()

def test_fail_closed_guard_missing_approvals():
    # AUD-001 is HIGH risk and should require approved 'active' state
    # Set its state to draft
    registry = get_registry()
    registry.update_prompt_state("AUD-001", "draft")
    
    # Try executing it
    response_fail = client.post("/api/prompts/AUD-001/run")
    assert response_fail.status_code == 403
    assert "Requires active approved state" in response_fail.json()["detail"]
    
    # Set it back to active (mocking approval)
    registry.update_prompt_state("AUD-001", "active")
    
    # Try executing again (should bypass approval check, might fail 500 on model but not 403)
    response_retry = client.post("/api/prompts/AUD-001/run")
    assert response_retry.status_code != 403

def test_fail_closed_guard_registry_not_live():
    registry = get_registry()
    orig_status = registry.status
    
    try:
        # Mock registry status to FAIL_CLOSED
        registry.status = "FAIL_CLOSED"
        
        response_fail = client.post("/api/prompts/QA-002/run")
        assert response_fail.status_code == 503
        assert "Registry is in 'FAIL_CLOSED' state" in response_fail.json()["detail"]
    finally:
        registry.status = orig_status
