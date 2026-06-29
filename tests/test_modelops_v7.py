import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.modelops_manager import ModelOpsManager
from pathlib import Path
import json
import os
import shutil

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_teardown_modelops_files():
    base_dir = Path(__file__).resolve().parent.parent
    reg_path = base_dir / "data" / "prompt_registry" / "model_registry.json"
    state_path = base_dir / "data" / "prompt_registry" / "modelops_state.json"
    
    # Backups
    reg_bak = base_dir / "data" / "prompt_registry" / "model_registry.json.bak"
    state_bak = base_dir / "data" / "prompt_registry" / "modelops_state.json.bak"
    
    if reg_path.exists():
        shutil.copy(reg_path, reg_bak)
    if state_path.exists():
        shutil.copy(state_path, state_bak)
        
    yield
    
    # Restore
    if reg_bak.exists():
        shutil.copy(reg_bak, reg_path)
        reg_bak.unlink()
    if state_bak.exists():
        shutil.copy(state_bak, state_path)
        state_bak.unlink()

def test_modelops_endpoints_exist_and_fetch():
    # 1. Fetch models
    res_models = client.get("/api/modelops/models")
    assert res_models.status_code == 200
    models = res_models.json()
    assert isinstance(models, list)
    assert len(models) >= 5
    assert models[0]["model_id"] == "ollama/llama3"

    # 2. Fetch routes
    res_routes = client.get("/api/modelops/routes")
    assert res_routes.status_code == 200
    routes = res_routes.json()
    assert "routing_policies" in routes
    assert "risk_guards" in routes

    # 3. Fetch metrics
    res_metrics = client.get("/api/modelops/metrics")
    assert res_metrics.status_code == 200
    metrics = res_metrics.json()
    assert "total_routed_requests" in metrics
    assert "health_breakdown" in metrics

def test_modelops_route_resolution():
    # Test coding task routing
    res = client.post("/api/modelops/route", json={"category": "CODE", "risk_level": "LOW"})
    assert res.status_code == 200
    data = res.json()
    assert data["model_id"] == "lm-studio/qwen2.5-coder-7b"
    assert data["best_for"] == "coding"

    # Test threat analysis routing
    res_threat = client.post("/api/modelops/route", json={"category": "Threat Analysis", "risk_level": "LOW"})
    assert res_threat.status_code == 200
    data_threat = res_threat.json()
    assert data_threat["model_id"] == "ollama/deepseek-r1"

def test_health_check_updates_status():
    res = client.get("/api/modelops/health")
    assert res.status_code == 200
    data = res.json()
    assert "timestamp" in data
    assert "report" in data
    assert len(data["report"]) >= 5

def test_evaluation_gate():
    # Trigger evaluation for ollama/codegemma
    res = client.post("/api/modelops/evals", json={"model_id": "ollama/codegemma"})
    assert res.status_code == 200
    data = res.json()
    assert data["model_id"] == "ollama/codegemma"
    assert "eval_score" in data
    assert "status" in data
    
    # Set model state manually via manager to simulate a failed eval
    mgr = ModelOpsManager()
    mgr.execute_eval("ollama/codegemma", simulated_score=0.80)
    mgr.execute_eval("lm-studio/qwen2.5-coder-7b", simulated_score=0.65)
    
    # Verify the model is now in failed_eval status
    models = mgr.load_models()
    model = next(m for m in models if m["model_id"] == "lm-studio/qwen2.5-coder-7b")
    assert model["status"] == "failed_eval"
    
    # Try routing to coding task (should trigger failover/fallback to ollama/codegemma)
    res_route = client.post("/api/modelops/route", json={"category": "CODE", "risk_level": "LOW"})
    assert res_route.status_code == 200
    assert res_route.json()["model_id"] == "ollama/codegemma"
    assert res_route.json()["fallback_used"] is True

def test_fail_closed_guards():
    mgr = ModelOpsManager()
    
    # 1. Block models with failed eval status
    mgr.execute_eval("ollama/deepseek-r1", simulated_score=0.50) # Failed reasoning model
    mgr.execute_eval("lm-studio/qwen2.5-7b-instruct", simulated_score=0.45) # Failed fallback model
    
    # Try routing threat analysis (both preferred and fallback reasoning models failed eval)
    res_route = client.post("/api/modelops/route", json={"category": "Threat Analysis", "risk_level": "LOW"})
    assert res_route.status_code == 400
    assert "FAILED_EVAL_STATUS" in res_route.json()["detail"]
    
    # 2. Block high-risk tasks if approved model is unavailable
    # AUD-001 is HIGH risk, category Audit (maps to reasoning model ollama/deepseek-r1)
    # Since deepseek-r1 is failed_eval, running prompt AUD-001 should be blocked by fail-closed guard
    res_run = client.post("/api/prompts/AUD-001/run")
    assert res_run.status_code in [400, 403, 503]
