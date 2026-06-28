import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.binding_readiness_manager import get_binding_readiness_status, run_binding_readiness_verification

client = TestClient(app)

def test_binding_readiness_status_structure():
    status = get_binding_readiness_status()
    assert "status" in status
    assert "readiness_score" in status
    assert "last_checked" in status
    assert "checkpoints" in status
    assert "logs" in status
    assert "compliance" in status
    
    # Assert correct compliance boundaries
    assert status["compliance"]["statement"] == "ATO-SUPPORTING EVIDENCE PACKAGE: READY FOR REVIEW"
    assert "Actual ATO has not been granted" in status["compliance"]["notice"]
    assert "No authorization claim is being made" in status["compliance"]["notice"]

def test_binding_readiness_verification_flow():
    # Run verification
    result = run_binding_readiness_verification()
    assert result["status"] in ["PASS", "FAIL"]
    assert len(result["checkpoints"]) == 9
    
    # Check that all checkpoints are completed
    for cp in result["checkpoints"]:
        assert cp["status"] in ["PASS", "FAIL"]

def test_binding_readiness_api_endpoints():
    # Test GET status
    resp = client.get("/api/v1/binding-readiness/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "readiness_score" in data
    
    # Test POST verify
    resp = client.post("/api/v1/binding-readiness/verify")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ["PASS", "FAIL"]
    
    # Verify no illegal/blocked authorization claims exist in returned dictionary
    forbidden_terms = ["ATO granted", "System authorized", "ATO complete", "Authorized to Operate"]
    data_str = str(data).lower()
    for term in forbidden_terms:
        assert term.lower() not in data_str
