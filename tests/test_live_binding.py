import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.live_binding_manager import get_live_binding_status, execute_live_binding, execute_live_rollback

client = TestClient(app)

def test_initial_live_binding_disconnected():
    status = get_live_binding_status()
    assert status["status"] == "DISCONNECTED"
    assert status["external_url"] is None
    assert status["metrics"]["tls_active"] is False
    assert status["metrics"]["auth_enforced"] is False
    assert status["compliance"]["statement"] == "CONTROLLED LIVE BINDING SIMULATION"
    assert "Actual ATO has not been granted" in status["compliance"]["notice"]
    assert "No authorization claim is being made" in status["compliance"]["notice"]

def test_live_binding_execution():
    status = execute_live_binding()
    assert status["status"] == "LIVE"
    assert status["external_url"] == "https://live-cockpit.clawde-tower.local:8443"
    assert status["metrics"]["tls_active"] is True
    assert status["metrics"]["auth_enforced"] is True
    assert status["metrics"]["network_exposed_port"] == 8443
    
    # Test subsequent rollback
    status_roll = execute_live_rollback()
    assert status_roll["status"] == "DISCONNECTED"
    assert status_roll["external_url"] is None
    assert status_roll["metrics"]["tls_active"] is False
    assert status_roll["metrics"]["network_exposed_port"] is None

def test_live_binding_endpoints():
    # Reset to disconnected first
    execute_live_rollback()
    
    # Test GET
    resp = client.get("/api/v1/live-binding/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "DISCONNECTED"
    
    # Test Execute POST
    resp = client.post("/api/v1/live-binding/execute")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "LIVE"
    assert data["external_url"] == "https://live-cockpit.clawde-tower.local:8443"
    
    # Validate no blocked/unauthorized claims exist in response
    blocked_claims = [
        "Live service active",
        "Public service operational",
        "Authorized to Operate",
        "ATO granted",
        "Risk eliminated",
        "100% secure"
    ]
    data_str = str(data).lower()
    for claim in blocked_claims:
        assert claim.lower() not in data_str
        
    # Test Rollback POST
    resp = client.post("/api/v1/live-binding/rollback")
    assert resp.status_code == 200
    assert resp.json()["status"] == "DISCONNECTED"
