import pytest
import os
import json
from pathlib import Path
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_promptops_metrics():
    response = client.get("/api/promptops/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "total_usage" in data
    assert "failure_rate" in data
    assert "stale_count" in data
    assert "quarantined_count" in data
    assert "approval_queue_count" in data
    assert data["total_prompts"] >= 400

def test_promptops_approvals_list():
    response = client.get("/api/promptops/approvals")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_promptops_drift():
    response = client.get("/api/promptops/drift")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_promptops_lifecycle_transitions():
    # 1. Quarantine
    response_quar = client.post("/api/promptops/prompts/AUD-001/quarantine")
    assert response_quar.status_code == 200
    assert response_quar.json()["status"] == "QUARANTINED"
    
    # Verify state updated in details
    response_det1 = client.get("/api/prompts/AUD-001")
    assert response_det1.json()["lifecycle_state"] == "quarantined"
    
    # 2. Archive
    response_arch = client.post("/api/promptops/prompts/AUD-001/archive")
    assert response_arch.status_code == 200
    assert response_arch.json()["status"] == "ARCHIVED"
    
    # Verify state updated
    response_det2 = client.get("/api/prompts/AUD-001")
    assert response_det2.json()["lifecycle_state"] == "archived"
    
    # 3. Approve back to active (Requires valid Owner/Role payload if high risk, AUD-001 is HIGH risk)
    # Check unauthorized approval
    response_app_fail = client.post(
        "/api/promptops/prompts/AUD-001/approve",
        json={"user": "Unauthorized Person", "role": "Intern"}
    )
    assert response_app_fail.status_code == 403
    
    # Check authorized approval
    response_app_ok = client.post(
        "/api/promptops/prompts/AUD-001/approve",
        json={"user": "Michael Hoch", "role": "Owner"}
    )
    assert response_app_ok.status_code == 200
    assert response_app_ok.json()["status"] == "APPROVED"
    
    # Verify state is active
    response_det3 = client.get("/api/prompts/AUD-001")
    assert response_det3.json()["lifecycle_state"] == "active"

def test_promptops_ci_gate():
    response = client.post("/api/promptops/ci-gate")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "errors" in data
