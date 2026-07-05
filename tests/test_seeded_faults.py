import os
import json
import sqlite3
import pytest
import subprocess
from pathlib import Path
from backend.runtime_truth.state_store import DB_PATH, apply_pragmas

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "has_live_project_tracker/data"

def test_visual_compliance_mutation():
    pert_server_path = ROOT / "backend/pert_server.py"
    assert pert_server_path.exists()
    
    # Backup original pert_server.py content
    original_content = pert_server_path.read_text(encoding="utf-8")
    try:
        # Mutate: remove the DOM ID 'hoch-pods-theater'
        mutated_content = original_content.replace('"hoch-pods-theater"', '"hoch-pods-theater-mutated"')
        pert_server_path.write_text(mutated_content, encoding="utf-8")
        
        # Run compliance audit script
        res = subprocess.run(
            ["python3", "scripts/audit_hoch_pods_theater_visual_compliance.py"],
            capture_output=True,
            text=True
        )
        # Assert that it fails!
        assert res.returncode != 0
        assert "ID_HOCH-PODS-THEATER" in res.stdout or "FAIL" in res.stdout
    finally:
        # Restore original file
        pert_server_path.write_text(original_content, encoding="utf-8")

def test_lease_fencing_mutation():
    proof_index_file = DATA_DIR / "ag_execution_proof_index.json"
    fencing_status_file = DATA_DIR / "ag_execution_fencing_status.json"
    
    # Backup
    backup_content = None
    if proof_index_file.exists():
        backup_content = proof_index_file.read_text(encoding="utf-8")
        
    backup_status = None
    if fencing_status_file.exists():
        backup_status = fencing_status_file.read_text(encoding="utf-8")
        
    try:
        # Mutate: seed non-monotonic tokens (proof 2 token is smaller than proof 1)
        mutated_data = {
            "proofs": [
                {
                    "task_id": "task-1",
                    "fencing_token": 100,
                    "status": "SUCCESS"
                },
                {
                    "task_id": "task-2",
                    "fencing_token": 90,
                    "status": "SUCCESS"
                }
            ]
        }
        with open(proof_index_file, "w") as f:
            json.dump(mutated_data, f)
            
        # Run fencing verification script
        res = subprocess.run(
            ["python3", "scripts/verify_ag_execution_fencing.py"],
            capture_output=True,
            text=True
        )
        # Assert that it fails!
        assert res.returncode != 0
        assert "Fencing token monotonicity violation" in res.stdout
    finally:
        # Restore
        if backup_content is not None:
            proof_index_file.write_text(backup_content, encoding="utf-8")
        elif proof_index_file.exists():
            proof_index_file.unlink()
            
        if backup_status is not None:
            fencing_status_file.write_text(backup_status, encoding="utf-8")
        elif fencing_status_file.exists():
            fencing_status_file.unlink()

def test_heartbeat_expiry_mutation():
    # Setup SQLite connection to inject stale heartbeat
    conn = sqlite3.connect(DB_PATH)
    apply_pragmas(conn)
    conn.row_factory = sqlite3.Row
    
    # Backup original heartbeats
    original_hb = [dict(r) for r in conn.execute("SELECT * FROM runtime_heartbeats").fetchall()]
    
    try:
        # Mutate: Delete all heartbeats and insert an expired one (2 hours old, ttl_ms = 10000)
        conn.execute("DELETE FROM runtime_heartbeats")
        conn.execute(
            "INSERT INTO runtime_heartbeats (component, last_seen, status, ttl_ms) VALUES (?, ?, ?, ?)",
            ("backend_core", "2026-07-05T00:00:00Z", "RUNNING", 10000)
        )
        conn.commit()
        
        # Run anti_fake_gate.sh which evaluates heartbeat freshness
        res = subprocess.run(
            ["bash", "scripts/anti_fake_gate.sh"],
            capture_output=True,
            text=True
        )
        # Assert that it fails!
        assert res.returncode != 0
        assert "FAIL" in res.stdout or "stale" in res.stdout.lower()
    finally:
        # Restore sqlite
        conn.execute("DELETE FROM runtime_heartbeats")
        for hb in original_hb:
            conn.execute(
                "INSERT INTO runtime_heartbeats (component, last_seen, status, ttl_ms) VALUES (?, ?, ?, ?)",
                (hb["component"], hb["last_seen"], hb["status"], hb.get("ttl_ms"))
            )
        conn.commit()
        conn.close()
