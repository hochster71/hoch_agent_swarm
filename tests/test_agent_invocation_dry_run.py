from backend.agent_invocation import AgentInvocation

def test_dry_run_invocation():
    invocation = AgentInvocation()
    agent = {
        "gene_id": "HASF-TEST-T2",
        "title": "T2 Planner",
        "version": "1.0.1",
        "content_hash": "abc123hash",
        "max_execution_tier": "T2_DRAFT_REMEDIATOR",
        "requires_human_approval": False,
        "outputs": "remediation_plan.yaml"
    }
    
    res = invocation.dry_run(agent, "Generate a remediation plan for CVE-2024-1234")
    
    assert res["selected_agent_id"] == "HASF-TEST-T2"
    assert res["prompt_version"] == "1.0.1"
    assert res["content_hash"] == "abc123hash"
    assert res["safety_tier"] == "T2_DRAFT_REMEDIATOR"
    assert res["approval_required"] is False
    assert "remediation_plan.yaml" in res["expected_outputs"]
    assert "DRY-RUN COMPLETED" in res["dry_run_result"]
