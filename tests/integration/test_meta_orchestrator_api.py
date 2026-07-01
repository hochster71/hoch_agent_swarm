import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_coverage_endpoint_responds_success():
    res = client.get("/api/v1/meta-orchestrator/coverage")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "metrics" in data
    assert "domains" in data

def test_gaps_endpoint_responds_success():
    res = client.get("/api/v1/meta-orchestrator/gaps")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert isinstance(data["gaps"], list)

def test_daily_brief_endpoint_responds_success():
    res = client.get("/api/v1/meta-orchestrator/daily-brief")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "brief" in data
    assert "evidence_paths" in data
