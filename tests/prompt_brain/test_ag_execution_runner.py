import json
from pathlib import Path
import pytest
from scripts.ag_execution_runner import run_executor
import scripts.ag_execution_runner as runner

def test_ag_executor_run(tmp_path, monkeypatch):
    # Setup mock files
    queue_file = tmp_path / "helm_task_queue.json"
    control_file = tmp_path / "orchestration_bridge_control.json"
    log_file = tmp_path / "helm_execution_log.json"
    state_file = tmp_path / "ag_execution_adapter_state.json"
    
    # Patch script variables to use mock paths
    monkeypatch.setattr(runner, "QUEUE_FILE", queue_file)
    monkeypatch.setattr(runner, "CONTROL_FILE", control_file)
    monkeypatch.setattr(runner, "LOG_FILE", log_file)
    monkeypatch.setattr(runner, "STATE_FILE", state_file)
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    
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
            "task_name": "Create a safe local file with micro-segmentation guidelines",
            "task_class": "file_modification",
            "allowed_agent": "hasf_builder_agent",
            "status": "PENDING"
        },
        {
            "task_id": "task-test-002",
            "task_name": "Setup Stripe monetization billing accounts",
            "task_class": "monetization",
            "allowed_agent": "hasf_builder_agent",
            "status": "PENDING"
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
    assert "ag_execution_proof.md" in updated_tasks[0]["result"]
    
    assert updated_tasks[1]["status"] == "BLOCKED"
    
    # Check log updates
    with open(log_file, "r") as f:
        logs = json.load(f)
    assert len(logs) == 1
    assert logs[0]["event"] == "ag_task_executed"
    assert logs[0]["task_id"] == "task-test-001"
    
    # Check proof exists
    proof_path = tmp_path / "docs/evidence/runtime/ag_execution_proof.md"
    assert proof_path.exists()
    assert "LOCAL_SAFE_WRITE" in proof_path.read_text()
