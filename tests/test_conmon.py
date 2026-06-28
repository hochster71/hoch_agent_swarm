import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.conmon_manager import get_conmon_status, execute_conmon_cycle, update_conmon_schedule

client = TestClient(app)

def test_initial_conmon_status():
    status = get_conmon_status()
    assert status["status"] == "IDLE"
    assert status["schedule_interval"] == "Daily"
    assert status["compliance_score"] == 88.0
    assert len(status["active_alerts"]) == 0
    assert status["compliance"]["statement"] == "SIMULATED CONTINUOUS COMPLIANCE POSTURE"
    assert "Actual ATO has not been granted" in status["compliance"]["notice"]
    assert "No authorization claim is being made" in status["compliance"]["notice"]

def test_conmon_schedule_update():
    status = update_conmon_schedule("Weekly")
    assert status["schedule_interval"] == "Weekly"
    
    # Restore to Daily
    status_daily = update_conmon_schedule("Daily")
    assert status_daily["schedule_interval"] == "Daily"

def test_conmon_cycle_execution():
    status = execute_conmon_cycle()
    assert len(status["history"]) > 0
    assert status["compliance_score"] >= 80.0
    
    # Check that a ConMon event was logged
    from backend.ledger_manager import get_ledger_blocks
    blocks = get_ledger_blocks()
    actions = []
    for b in blocks:
        evt = b.get("event", {})
        if "action" in evt:
            act = evt["action"]
            if isinstance(act, dict):
                actions.append(act.get("name"))
            else:
                actions.append(str(act))
    assert "conmon_compliance_evaluation" in actions

def test_conmon_api_endpoints():
    # Test GET
    resp = client.get("/api/v1/conmon/status")
    assert resp.status_code == 200
    assert resp.json()["schedule_interval"] == "Daily"
    
    # Test Update POST
    resp = client.post("/api/v1/conmon/schedule/update", json={"interval": "Hourly"})
    assert resp.status_code == 200
    assert resp.json()["schedule_interval"] == "Hourly"
    
    # Test Run POST
    resp = client.post("/api/v1/conmon/run")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["history"]) > 0
    
    # Validate no blocked/unauthorized claims exist in response
    blocked_claims = [
        "Public service operational",
        "Externally exposed production service",
        "Authorized to Operate",
        "ATO granted",
        "Risk eliminated",
        "100% secure"
    ]
    data_str = str(data).lower()
    for claim in blocked_claims:
        assert claim.lower() not in data_str
