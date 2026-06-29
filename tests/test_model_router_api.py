import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_model_router_config_endpoints():
    # 1. Get initial configuration
    get_res = client.get("/api/v1/models/registry")
    assert get_res.status_code == 200
    config_data = get_res.json()
    assert "default_provider" in config_data
    assert "default_model" in config_data

    # Save initial values to restore later
    old_provider = config_data.get("default_provider")
    old_model = config_data.get("default_model")

    # 2. Update configuration
    config_data["default_provider"] = "ollama"
    config_data["default_model"] = "llama3.1:8b"
    config_data["local_first"] = True
    config_data["paid_models_enabled"] = False
    
    post_res = client.post("/api/v1/models/router/config", json=config_data)
    assert post_res.status_code == 200
    assert post_res.json()["status"] == "SUCCESS"

    # Verify change took effect
    get_res_2 = client.get("/api/v1/models/registry")
    assert get_res_2.status_code == 200
    assert get_res_2.json()["default_provider"] == "ollama"
    assert get_res_2.json()["default_model"] == "llama3.1:8b"

    # Restore old config
    config_data["default_provider"] = old_provider
    config_data["default_model"] = old_model
    client.post("/api/v1/models/router/config", json=config_data)

def test_task_evidence_endpoint_404():
    get_res = client.get("/api/v1/runs/invalid-run/tasks/invalid-task/evidence")
    assert get_res.status_code == 404

def test_task_evidence_success():
    from backend.runtime_execution_store import persist_swarm_run, persist_swarm_task
    import uuid

    run_id = f"run-{uuid.uuid4()}"
    task_id = f"task-{uuid.uuid4()}"

    persist_swarm_run(run_id, "Test API Run", "running")
    persist_swarm_task({
        "id": task_id,
        "run_id": run_id,
        "title": "Test Title",
        "description": "Test Description",
        "status": "running",
        "priority": "high",
        "ownerAgentId": "test-agent",
        "dependencies": [],
        "planningFrameworks": [],
        "acceptanceCriteria": "done",
        "riskLevel": "low",
        "approvalRequired": False
    })

    get_res = client.get(f"/api/v1/runs/{run_id}/tasks/{task_id}/evidence")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["task"]["id"] == task_id
    assert data["task"]["title"] == "Test Title"
    assert "tool_calls" in data
    assert "validation_evidence" in data
    assert "model_routing" in data
