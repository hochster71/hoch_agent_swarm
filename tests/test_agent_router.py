import pytest
import json
from pathlib import Path
from backend.agent_router import AgentRouter

def test_agent_routing_fail_closed(tmp_path):
    router = AgentRouter(base_dir=tmp_path)
    # Ensure missing report forces fail-closed
    with pytest.raises(ValueError, match="Registry status is not GO"):
        router.route({"domain": "QA"})

def test_agent_routing_success():
    router = AgentRouter()
    # Route valid task
    res = router.route({
        "domain": "QA",
        "industry": "NorthStar Swarm OS",
        "mission_phase": "Pre-Release Verification",
        "runtime_role": "Auditor",
        "risk_level": "LOW"
    })
    
    assert res["winner"] is not None
    assert res["winner"]["status"] == "active"
    # Ensure deprecated alias is never selected as active
    assert not res["winner"]["gene_id"].startswith("gapfill-")
