import json
from pathlib import Path
import pytest
from scripts.ag_execution_runner import run_executor
import scripts.ag_execution_runner as runner
import scripts.ag_execution_lease_manager as lm_module

def test_ag_executor_run(tmp_path, monkeypatch):
    # Setup mock files
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

    # Patch script variables to use mock paths
    monkeypatch.setattr(runner, "QUEUE_FILE", queue_file)
    monkeypatch.setattr(runner, "CONTROL_FILE", control_file)
    monkeypatch.setattr(runner, "LOG_FILE", log_file)
    monkeypatch.setattr(runner, "STATE_FILE", state_file)
    monkeypatch.setattr(runner, "HOLD_FILE", hold_file)
    monkeypatch.setattr(runner, "RETRY_POLICY_FILE", retry_policy_file)
    monkeypatch.setattr(runner, "POLICY_FILE", policy_file)
    monkeypatch.setattr(runner, "FAILURES_FILE", failures_file)
    monkeypatch.setattr(runner, "PROOF_INDEX_FILE", proof_index_file)
    monkeypatch.setattr(runner, "ROOT", tmp_path)

    monkeypatch.setattr(lm_module, "LEASES_FILE", leases_file)
    monkeypatch.setattr(lm_module, "LOCK_FILE", lock_file)

    # Initialize empty registries
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
                "action_prefixes": ["create_"],
                "risk_tier_max": "R2"
            },
            "blocked_monetization": {
                "keywords": ["stripe", "billing"],
                "risk_tier_max": "R4"
            }
        }
    }), encoding="utf-8")

    # 1. Test when AG execution is disabled
    control_file.write_text(json.dumps({"allow_ag_execution": False}), encoding="utf-8")
    with pytest.raises(SystemExit):
        run_executor() # Should exit early without creating state/logs
    assert not state_file.exists()
    
    # 2. Test execution of a safe pending task
    control_file.write_text(json.dumps({"allow_ag_execution": True}), encoding="utf-8")
    
    tasks = [
        {
            "task_id": "task-test-001",
            "task_name": "create_a_safe_local_file",
            "task_class": "file_modification",
            "allowed_agent": "hasf_builder_agent",
            "status": "PENDING",
            "attempts": 0
        },
        {
            "task_id": "task-test-002",
            "task_name": "stripe_setup",
            "task_class": "monetization",
            "allowed_agent": "hasf_builder_agent",
            "status": "PENDING",
            "attempts": 0
        }
    ]
    queue_file.write_text(json.dumps(tasks, indent=2), encoding="utf-8")
    
    state_file.write_text(json.dumps({"status": "IDLE"}), encoding="utf-8")
    
    run_executor()
    
    # Check queue updates
    with open(queue_file, "r") as f:
        updated_tasks = json.load(f)
        
    assert updated_tasks[0]["status"] == "completed"
    assert updated_tasks[0]["completed_at"] is not None
    assert "ag_execution_proof_task-test-001.md" in updated_tasks[0]["result"]
    
    assert updated_tasks[1]["status"] == "BLOCKED"
    
    # Check log updates
    with open(log_file, "r") as f:
        logs = json.load(f)
    assert len(logs) == 1
    assert logs[0]["event"] == "ag_task_executed"
    assert logs[0]["task_id"] == "task-test-001"
    
    # Check proof exists
    proof_path = tmp_path / "docs/evidence/runtime/ag_execution_proof_task-test-001.md"
    assert proof_path.exists()
    assert "SUCCESS" in proof_path.read_text()
