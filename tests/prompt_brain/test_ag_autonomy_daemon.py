import os
import json
import datetime
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.main import app
from scripts.ag_execution_lease_manager import LeaseManager

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "has_live_project_tracker/data"
HOLD_FILE = DATA_DIR / "ag_operator_hold.json"
STATE_FILE = DATA_DIR / "ag_execution_daemon_state.json"
HEARTBEAT_FILE = DATA_DIR / "ag_daemon_heartbeat_status.json"
FENCING_FILE = DATA_DIR / "ag_execution_fencing_status.json"

@pytest.fixture
def client():
    return TestClient(app)

def test_daemon_endpoints(client):
    # Verify GET endpoints
    res = client.get("/api/autonomy/daemon/state")
    assert res.status_code == 200
    assert "daemon_status" in res.json()

    res = client.get("/api/autonomy/daemon/heartbeat")
    assert res.status_code == 200
    assert "verdict" in res.json()

    res = client.get("/api/autonomy/daemon/oracle")
    assert res.status_code == 200

    res = client.get("/api/autonomy/daemon/fencing")
    assert res.status_code == 200

def test_operator_hold_precedence(client):
    # Set Operator Hold active
    hold_data = {
        "operator_hold_active": True,
        "reason": "Test emergency stop",
        "operator": "Pytest",
        "timestamp": "2026-07-05T00:00:00Z",
        "affected_categories": []
    }
    with open(HOLD_FILE, "w") as f:
        json.dump(hold_data, f, indent=2)
        
    # POST /api/autonomy/daemon/operator-start should be rejected
    res = client.post("/api/autonomy/daemon/operator-start")
    assert res.status_code == 400
    assert "Operator Hold is active" in res.json()["detail"]
    
    # Disable hold via API
    res = client.post("/api/autonomy/daemon/operator-stop")
    assert res.status_code == 200
    assert res.json()["payload"]["operator_hold_active"] is True
    
    # Manually clear hold to clean up
    hold_data["operator_hold_active"] = False
    with open(HOLD_FILE, "w") as f:
        json.dump(hold_data, f, indent=2)

def test_lease_fencing_tokens():
    # Force delete lock file to clear any stale state
    lock_file = DATA_DIR / "ag_execution_lock.json"
    if lock_file.exists():
        lock_file.unlink()

    lm = LeaseManager()
    
    # Acquire first lease
    lease1 = lm.acquire_lease("task-fence-1", "test-runner-1", 10)
    assert lease1 is not None
    assert "fencing_token" in lease1
    token1 = lease1["fencing_token"]
    
    # Release first lease so we can acquire a second one
    lm.release_lease(lease1["lease_id"])
    
    # Acquire second lease
    lease2 = lm.acquire_lease("task-fence-2", "test-runner-2", 10)
    assert lease2 is not None
    assert lease2["fencing_token"] > token1
    
    # Cleanup leases
    lm.release_lease(lease2["lease_id"])

def test_zombie_writer_rejected():
    queue_file = DATA_DIR / "helm_task_queue.json"
    proof_index_file = DATA_DIR / "ag_execution_proof_index.json"
    lock_file = DATA_DIR / "ag_execution_lock.json"
    control_file = DATA_DIR / "orchestration_bridge_control.json"
    hold_file = DATA_DIR / "ag_operator_hold.json"
    leases_file = DATA_DIR / "ag_execution_leases.json"
    
    # Save backups of existing files
    backups = {}
    for path in [queue_file, proof_index_file, lock_file, control_file, hold_file, leases_file]:
        if path.exists():
            backups[path] = path.read_text(encoding="utf-8")
            
    try:
        # 1. Enable execution
        with open(control_file, "w") as f:
            json.dump({"allow_ag_execution": True}, f)
        # Disable hold
        with open(hold_file, "w") as f:
            json.dump({"operator_hold_active": False}, f)
            
        # 2. Seed a completed proof in index with fencing token 100
        proof_index_data = {
            "proofs": [
                {
                    "task_id": "task-old-01",
                    "lease_id": "lease-old-01",
                    "fencing_token": 100,
                    "status": "SUCCESS"
                }
            ]
        }
        with open(proof_index_file, "w") as f:
            json.dump(proof_index_data, f, indent=2)
            
        # 3. Add a pending task in queue
        task_id = "task-zombie-test"
        task_queue = [
            {
                "task_id": task_id,
                "task_name": "verify_zombie_task",
                "task_class": "verify",
                "status": "PENDING",
                "allowed_agent": "hasf_builder_agent",
                "attempts": 0
            }
        ]
        with open(queue_file, "w") as f:
            json.dump(task_queue, f, indent=2)
            
        # 4. Seed the leases history so that the next acquired lease gets token 90 (stale!)
        leases_data = [
            {
                "lease_id": "lease-dummy-1",
                "task_id": "task-dummy-1",
                "status": "RELEASED",
                "fencing_token": 89
            }
        ]
        with open(leases_file, "w") as f:
            json.dump(leases_data, f, indent=2)
            
        # Clear active lock file
        if lock_file.exists():
            lock_file.unlink()
            
        # 5. Run the executor and assert it handles stale writers correctly
        from scripts.ag_execution_runner import run_executor
        run_executor()
            
        # 6. Verify that the task was BLOCKED
        with open(queue_file, "r") as f:
            updated_queue = json.load(f)
        assert updated_queue[0]["status"] == "BLOCKED"
        
        # Verify runner state transitioned to BLOCKED_BY_POLICY
        state_file = DATA_DIR / "ag_execution_adapter_state.json"
        with open(state_file, "r") as f:
            state_data = json.load(f)
        assert state_data["status"] == "BLOCKED_BY_POLICY"
        
    finally:
        # Restore backups
        for path, content in backups.items():
            path.write_text(content, encoding="utf-8")
        # Clean up temporary ones that didn't exist before
        for path in [queue_file, proof_index_file, lock_file, control_file, hold_file, leases_file]:
            if path not in backups and path.exists():
                path.unlink()

def test_readiness_caps_heartbeat_and_idle_with_pending():
    import sqlite3
    from backend.final_verifier.readiness_cap_engine import ReadinessCapEngine
    
    queue_file = DATA_DIR / "helm_task_queue.json"
    daemon_state_file = DATA_DIR / "ag_execution_daemon_state.json"
    
    # Backup
    backups = {}
    for path in [queue_file, daemon_state_file]:
        if path.exists():
            backups[path] = path.read_text(encoding="utf-8")
            
    # Setup SQLite connection to clean heartbeats table for this test
    from backend.runtime_truth.state_store import DB_PATH, apply_pragmas
    conn = sqlite3.connect(DB_PATH)
    apply_pragmas(conn)
    
    # Backup heartbeats
    conn.row_factory = sqlite3.Row
    original_hb = [dict(r) for r in conn.execute("SELECT * FROM runtime_heartbeats").fetchall()]
    
    try:
        # 1. Test stale heartbeat cap
        conn.execute("DELETE FROM runtime_heartbeats")
        # Insert a very old heartbeat (e.g. 1 hour ago) with ttl_ms = 5000 (5 seconds)
        conn.execute(
            "INSERT INTO runtime_heartbeats (component, last_seen, status, ttl_ms) VALUES (?, ?, ?, ?)",
            ("backend_core", "2026-07-05T00:00:00Z", "RUNNING", 5000)
        )
        conn.commit()
        
        engine = ReadinessCapEngine(db_path=DB_PATH)
        res = engine.calculate_caps()
        assert res["score"] <= 50.0
        assert any("stale component heartbeat" in cap for cap in res["caps"])
        
        # 2. Test idle-with-pending cap
        # Clear heartbeats and add a fresh one for the daemon so that only the idle cap triggers
        conn.execute("DELETE FROM runtime_heartbeats")
        conn.execute(
            "INSERT INTO runtime_heartbeats (component, last_seen, status, ttl_ms) VALUES (?, ?, ?, ?)",
            ("ag_execution_daemon", datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"), "RUNNING", 10000)
        )
        conn.commit()
        
        # Write pending tasks to queue
        task_queue = [{"task_id": "t1", "status": "PENDING"}]
        with open(queue_file, "w") as f:
            json.dump(task_queue, f)
            
        # Write IDLE state to daemon state file
        daemon_state = {"daemon_status": "IDLE", "last_cycle_status": "IDLE"}
        with open(daemon_state_file, "w") as f:
            json.dump(daemon_state, f)
            
        res = engine.calculate_caps()
        assert res["score"] <= 50.0
        assert "stuck daemon: idle with pending tasks" in res["caps"]
        
    finally:
        # Restore backups
        for path, content in backups.items():
            path.write_text(content, encoding="utf-8")
        for path in [queue_file, daemon_state_file]:
            if path not in backups and path.exists():
                path.unlink()
                
        # Restore sqlite
        conn.execute("DELETE FROM runtime_heartbeats")
        for hb in original_hb:
            conn.execute(
                "INSERT INTO runtime_heartbeats (component, last_seen, status, ttl_ms) VALUES (?, ?, ?, ?)",
                (hb["component"], hb["last_seen"], hb["status"], hb.get("ttl_ms"))
            )
        conn.commit()
        conn.close()


