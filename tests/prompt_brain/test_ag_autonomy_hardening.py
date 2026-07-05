import os
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.main import app
import scripts.ag_execution_lease_manager as lm_module
import scripts.ag_execution_runner as runner_module
import scripts.ag_operator_hold as hold_module

client = TestClient(app)

@pytest.fixture
def mock_paths(tmp_path, monkeypatch):
    queue_file = tmp_path / "helm_task_queue.json"
    control_file = tmp_path / "orchestration_bridge_control.json"
    log_file = tmp_path / "helm_execution_log.json"
    state_file = tmp_path / "ag_execution_adapter_state.json"
    hold_file = tmp_path / "ag_operator_hold.json"
    retry_policy_file = tmp_path / "ag_execution_retry_policy.json"
    policy_file = tmp_path / "ag_execution_policy.json"
    failures_file = tmp_path / "ag_execution_failures.jsonl"
    proof_index_file = tmp_path / "ag_execution_proof_index.json"
    leases_file = tmp_path / "ag_execution_leases.json"
    lock_file = tmp_path / "ag_execution_lock.json"

    # Patch runner paths
    monkeypatch.setattr(runner_module, "QUEUE_FILE", queue_file)
    monkeypatch.setattr(runner_module, "CONTROL_FILE", control_file)
    monkeypatch.setattr(runner_module, "LOG_FILE", log_file)
    monkeypatch.setattr(runner_module, "STATE_FILE", state_file)
    monkeypatch.setattr(runner_module, "HOLD_FILE", hold_file)
    monkeypatch.setattr(runner_module, "RETRY_POLICY_FILE", retry_policy_file)
    monkeypatch.setattr(runner_module, "POLICY_FILE", policy_file)
    monkeypatch.setattr(runner_module, "FAILURES_FILE", failures_file)
    monkeypatch.setattr(runner_module, "PROOF_INDEX_FILE", proof_index_file)
    monkeypatch.setattr(runner_module, "ROOT", tmp_path)

    # Patch lease manager paths
    monkeypatch.setattr(lm_module, "LEASES_FILE", leases_file)
    monkeypatch.setattr(lm_module, "LOCK_FILE", lock_file)

    # Patch operator hold paths
    monkeypatch.setattr(hold_module, "HOLD_FILE", hold_file)

    # Write initial configs
    control_file.write_text(json.dumps({"allow_ag_execution": True}), encoding="utf-8")
    hold_file.write_text(json.dumps({"operator_hold_active": False}), encoding="utf-8")
    retry_policy_file.write_text(json.dumps({
        "max_retries": 3,
        "initial_backoff_seconds": 1,
        "backoff_multiplier": 1,
        "non_retryable_categories": ["monetization", "release"]
    }), encoding="utf-8")
    policy_file.write_text(json.dumps({
        "policy_categories": {
            "allowed_internal_task": {
                "action_prefixes": ["read_", "analyze_"],
                "risk_tier_max": "R2"
            },
            "blocked_monetization": {
                "keywords": ["stripe", "billing"],
                "risk_tier_max": "R4"
            }
        }
    }), encoding="utf-8")

    return {
        "queue_file": queue_file,
        "control_file": control_file,
        "log_file": log_file,
        "state_file": state_file,
        "hold_file": hold_file,
        "retry_policy_file": retry_policy_file,
        "policy_file": policy_file,
        "failures_file": failures_file,
        "proof_index_file": proof_index_file,
        "leases_file": leases_file,
        "lock_file": lock_file
    }

def test_lease_acquisition_and_release(mock_paths):
    lm = lm_module.LeaseManager()
    
    # 1. Acquire lease
    lease = lm.acquire_lease("task-123", "test_holder", 10)
    assert lease is not None
    assert lease["status"] == "ACTIVE"
    assert lease["task_id"] == "task-123"

    # 2. Prevent duplicate active lease
    duplicate = lm.acquire_lease("task-456", "another_holder", 10)
    assert duplicate is None

    # 3. Release lease
    released = lm.release_lease(lease["lease_id"])
    assert released is True

    # 4. Re-acquire works now
    next_lease = lm.acquire_lease("task-456", "another_holder", 10)
    assert next_lease is not None

def test_operator_hold_behavior(mock_paths, monkeypatch):
    paths = mock_paths
    paths["hold_file"].write_text(json.dumps({
        "operator_hold_active": True,
        "reason": "Emergency Halt"
    }), encoding="utf-8")

    # Runner should exit early with SystemExit due to operator hold
    with pytest.raises(SystemExit):
        runner_module.run_executor()

    state = json.loads(paths["state_file"].read_text(encoding="utf-8"))
    assert state["status"] == "BLOCKED_BY_POLICY"

def test_policy_classification_and_execution(mock_paths):
    paths = mock_paths
    
    # Create two tasks: one allowed, one blocked
    queue_tasks = [
        {
            "task_id": "task-allowed",
            "task_name": "read_and_analyze_data",
            "task_class": "internal",
            "status": "PENDING",
            "allowed_agent": "hasf_builder_agent",
            "attempts": 0
        },
        {
            "task_id": "task-blocked",
            "task_name": "stripe_charge_customer",
            "task_class": "billing",
            "status": "PENDING",
            "allowed_agent": "hasf_builder_agent",
            "attempts": 0
        }
    ]
    paths["queue_file"].write_text(json.dumps(queue_tasks), encoding="utf-8")

    runner_module.run_executor()

    updated_queue = json.loads(paths["queue_file"].read_text(encoding="utf-8"))
    
    allowed = next(t for t in updated_queue if t["task_id"] == "task-allowed")
    blocked = next(t for t in updated_queue if t["task_id"] == "task-blocked")

    assert allowed["status"] == "completed"
    assert blocked["status"] == "BLOCKED"

def test_autonomy_api_endpoints():
    # Verify GET routes
    res1 = client.get("/api/autonomy/execution/state")
    assert res1.status_code == 200
    
    res2 = client.get("/api/autonomy/execution/leases")
    assert res2.status_code == 200

    res3 = client.get("/api/autonomy/execution/policy")
    assert res3.status_code == 200

    res4 = client.get("/api/autonomy/execution/proofs")
    assert res4.status_code == 200

    res5 = client.get("/api/autonomy/execution/queue-health")
    assert res5.status_code == 200

    # Verify POST operator hold
    post_res = client.post("/api/autonomy/execution/operator-hold", json={
        "enable": True,
        "reason": "Test manual override",
        "operator": "Developer Unit Test",
        "categories": ["release"]
    })
    assert post_res.status_code == 200
    assert post_res.json()["payload"]["operator_hold_active"] is True
