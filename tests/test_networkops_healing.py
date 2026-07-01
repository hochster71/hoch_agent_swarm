import os
import sys
import json
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.networkops_manager import NetworkOpsManager

def test_networkops_status():
    manager = NetworkOpsManager()
    status = manager.get_status()
    assert "performance_score" in status
    assert "metrics" in status
    assert "speed_mbps" in status["metrics"]
    assert "latency_ms" in status["metrics"]

def test_networkops_incidents():
    manager = NetworkOpsManager()
    incidents = manager.get_incidents()
    assert len(incidents) >= 4
    ids = [i["incident_id"] for i in incidents]
    assert "inc-001" in ids
    assert "inc-002" in ids
    assert "inc-003" in ids

def test_networkops_run_diagnostics():
    manager = NetworkOpsManager()
    res = manager.run_diagnostics()
    assert res["status"] == "complete"
    assert "diagnostics_run_at" in res
    
    # Verify safe incident inc-004 is resolved
    incidents = manager.get_incidents()
    inc004 = next(i for i in incidents if i["incident_id"] == "inc-004")
    assert inc004["status"] == "resolved"

def test_execute_remediation_denied_without_approval():
    manager = NetworkOpsManager()
    # Ensure inc-001 is set to pending_approval
    incidents = manager.get_incidents()
    for inc in incidents:
        if inc["incident_id"] == "inc-001":
            inc["status"] = "pending_approval"
    manager._save_incidents(incidents)

    # Attempt to remediate with empty approvals queue
    res = manager.execute_remediation("inc-001", [])
    assert res["status"] == "denied"
    assert res["requires_approval"] is True

def test_execute_remediation_allowed_with_approval():
    manager = NetworkOpsManager()
    # Reset status
    incidents = manager.get_incidents()
    for inc in incidents:
        if inc["incident_id"] == "inc-001":
            inc["status"] = "pending_approval"
    manager._save_incidents(incidents)

    # Create mock approved gate
    approvals = [
        {
            "request_id": "inc-001",
            "status": "approved",
            "action_type": "REMEDIATE_inc-001"
        }
    ]

    res = manager.execute_remediation("inc-001", approvals)
    assert res["status"] == "success"
    assert "executed: Switch AP-Kitchen" in res["message"]
    assert res["rollback_plan"] == "Restore AP-Kitchen 2.4GHz channel to 11."

    # Verify status is now resolved in DB
    incidents = manager.get_incidents()
    inc001 = next(i for i in incidents if i["incident_id"] == "inc-001")
    assert inc001["status"] == "resolved"
