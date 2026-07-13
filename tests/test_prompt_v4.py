import pytest
import os
import json
from pathlib import Path
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)
base_dir = Path(__file__).resolve().parent.parent

def test_get_prompts():
    response = client.get("/api/prompts")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 400
    # Check shape of first prompt
    p = data[0]
    assert "id" in p
    assert "title" in p
    assert "category" in p
    assert "prompt" in p or "prompt_text" in p

def test_get_prompt_by_id():
    # Valid ID
    response = client.get("/api/prompts/AUD-001")
    assert response.status_code == 200
    p = response.json()
    assert p["id"] == "AUD-001"
    assert "title" in p
    
    # Invalid ID
    response_invalid = client.get("/api/prompts/INVALID-ID-999")
    assert response_invalid.status_code == 404

def test_get_prompts_metrics():
    response = client.get("/api/prompts/metrics")
    assert response.status_code == 200
    metrics = response.json()
    assert metrics["total_prompts"] >= 400
    assert "categories" in metrics
    assert "industries" in metrics
    assert "severities" in metrics
    assert "fixtures_summary" in metrics

def test_run_prompt(monkeypatch):
    from backend.model_gateway import ModelGateway
    monkeypatch.setattr(ModelGateway, "generate", lambda self, *args, **kwargs: "Mocked LLM response.")
    # Test execution for a valid prompt ID
    response = client.post("/api/prompts/AUD-001/run")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "COMPLETED"
    assert "evidence_file" in data
    assert "result" in data
    
    # Verify evidence file exists on disk
    evidence_path = base_dir / data["evidence_file"]
    assert evidence_path.exists()
    
    # Read and verify evidence content
    with open(evidence_path, "r", encoding="utf-8") as f:
        ev_data = json.load(f)
        assert ev_data["prompt_id"] == "AUD-001"
        assert "executed_at" in ev_data
        assert "task_request" in ev_data
        assert "execution_result" in ev_data
        
    # Clean up evidence file
    try:
        os.remove(evidence_path)
    except OSError:
        pass

def test_run_golden_fixtures_endpoint():
    response = client.post("/api/prompts/qa/golden-fixtures")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "total_fixtures" in data
    assert "passed_fixtures" in data
    assert data["passed_fixtures"] >= 20
