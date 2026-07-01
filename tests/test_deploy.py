import pytest
from backend.deployment_manager import get_deployment_status, execute_production_deployment
from backend.main import api_get_deployment_status, api_execute_production_deployment

def test_get_deployment_status():
    res = get_deployment_status()
    assert res["status"] in ["NOT_STARTED", "IN_PROGRESS", "SUCCESS", "ROLLED_BACK"]
    assert "logs" in res
    assert "compliance" in res
    assert res["compliance"]["statement"] == "ATO-SUPPORTING EVIDENCE PACKAGE: READY FOR REVIEW"
    assert "The system has ATO-supporting evidence prepared for review" in res["compliance"]["notice"]
    assert "Actual ATO has not been granted" in res["compliance"]["notice"]
    assert "No authorization claim is being made" in res["compliance"]["notice"]

def test_execute_production_deployment():
    res = execute_production_deployment()
    assert res["status"] == "SUCCESS"
    assert "checkpoints" in res
    assert len(res["checkpoints"]) > 0
    
    # Verify presence of checkpoints
    names = [cp["name"] for cp in res["checkpoints"]]
    assert "Runtime Package Integrity" in names
    assert "Kubernetes Service Deployment" in names
    assert "Health Probe Proximity Check" in names
    
    # Verify logs captured validation steps
    logs = "\n".join(res["logs"])
    assert "Starting production deployment sequence" in logs
    assert "launch.sh" in logs
    assert "healthcheck.sh" in logs
    assert "rollback_capsule.sh" in logs

def test_deployment_endpoints():
    res_status = api_get_deployment_status()
    assert "compliance" in res_status
    
    res_exec = api_execute_production_deployment()
    assert res_exec["status"] == "SUCCESS"
