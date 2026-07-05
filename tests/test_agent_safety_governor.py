from backend.agent_safety_governor import AgentSafetyGovernor

def test_safety_governor_evaluation():
    governor = AgentSafetyGovernor()
    
    # T1 read-only agent (auto-allowed)
    t1_agent = {
        "gene_id": "HASF-TEST-T1",
        "max_execution_tier": "T1_EVIDENCE_COLLECTOR",
        "task_class": "QA",
        "title": "T1 Auditor",
        "prompt": "Auditing task details..."
    }
    res_t1 = governor.evaluate_action(t1_agent, {"sandbox_active": False, "human_approved": False})
    assert res_t1["action_allowed"] is True
    assert res_t1["approval_required"] is False
    
    # T3 staged write agent (requires approval)
    t3_agent = {
        "gene_id": "HASF-TEST-T3",
        "max_execution_tier": "T3_STAGED_WRITER",
        "task_class": "Incident-Response",
        "title": "T3 Staged Remediator",
        "prompt": "Apply remediation script."
    }
    res_t3 = governor.evaluate_action(t3_agent, {"sandbox_active": False, "human_approved": False})
    assert res_t3["action_allowed"] is False
    assert res_t3["approval_required"] is True
    assert res_t3["verdict"] == "BLOCKED_APPROVAL_REQUIRED"

    # T4 controlled execution (requires sandbox marker)
    t4_agent = {
        "gene_id": "HASF-TEST-T4",
        "max_execution_tier": "T4_CONTROLLED_EXECUTOR",
        "task_class": "Self-Healing",
        "title": "T4 Restarter",
        "prompt": "Restart services."
    }
    res_t4_no_sandbox = governor.evaluate_action(t4_agent, {"sandbox_active": False, "human_approved": True})
    assert res_t4_no_sandbox["action_allowed"] is False
    assert res_t4_no_sandbox["verdict"] == "FAIL_CLOSED"

    res_t4_ok = governor.evaluate_action(t4_agent, {"sandbox_active": True, "human_approved": True})
    assert res_t4_ok["action_allowed"] is True

    # High-risk advisory category (Healthcare)
    healthcare_agent = {
        "gene_id": "HASF-TEST-MED",
        "max_execution_tier": "T1_EVIDENCE_COLLECTOR",
        "task_class": "Healthcare",
        "title": "Health Advisor",
        "prompt": "Diagnose symptoms."
    }
    res_med = governor.evaluate_action(healthcare_agent, {"sandbox_active": False, "human_approved": False})
    assert res_med["action_allowed"] is False
    assert res_med["approval_required"] is True
    assert res_med["verdict"] == "BLOCKED_APPROVAL_REQUIRED"
