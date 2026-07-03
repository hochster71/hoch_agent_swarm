import os
import json
from pathlib import Path
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "prompt_brain"

def test_effectiveness_endpoint():
    response = client.get("/api/prompt-brain/effectiveness")
    assert response.status_code == 200
    data = response.json()
    assert "evaluations" in data
    assert len(data["evaluations"]) == 8
    
    wins = sum(1 for e in data["evaluations"] if e["winner"] == "Prompt Brain")
    assert wins >= 6

def test_benchmark_results_endpoint():
    response = client.get("/api/prompt-brain/benchmark-results")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 8
    assert data[0]["domain"] == "DevSecOps pipeline hardening"

def test_red_team_gate_audit_endpoint():
    response = client.get("/api/prompt-brain/red-team-gate-audit")
    assert response.status_code == 200
    data = response.json()
    assert "total_rejected" in data
    assert data["total_rejected"] > 0

def test_model_adapters_status_endpoint():
    response = client.get("/api/prompt-brain/model-adapters/status")
    assert response.status_code == 200
    data = response.json()
    assert "HOCH Simulation" in data
    assert data["HOCH Simulation"]["is_available"] is True

def test_model_adapters_healthcheck_endpoint():
    response = client.post("/api/prompt-brain/model-adapters/healthcheck")
    assert response.status_code == 200
    data = response.json()
    assert "HOCH Simulation" in data
    assert data["HOCH Simulation"]["is_available"] is True

def test_execute_live_endpoint():
    response = client.post("/api/prompt-brain/runtime/execute-live", json={
        "domain": "Cybersecurity",
        "role": "Cybersecurity Engineer",
        "task": "Establish zero-trust network boundaries and micro-segmentation guidelines.",
        "family": "SOP Prompt"
    })
    assert response.status_code == 200
    data = response.json()
    assert "execution_id" in data
    assert data["passed"] is True
    assert data["execution_mode"] in ["live_model", "simulated"]

def test_weak_prompt_failure_injection_blocking():
    # Trigger an execution that is forced to fail, mimicking a critical safety audit block
    response = client.post("/api/prompt-brain/runtime/execute-live", json={
        "domain": "Cybersecurity",
        "role": "Cybersecurity Engineer",
        "task": "Establish zero-trust network boundaries.",
        "family": "SOP Prompt",
        "force_fail": True
    })
    assert response.status_code == 200
    data = response.json()
    assert data["repair_status"] == "REPAIRED"
    assert data["passed"] is True # Auto-repaired and approved
