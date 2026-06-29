from backend.coding_control_plane.coding_agent_router import CodingAgentRouter
from backend.coding_control_plane.agent_scoreboard import AgentScoreboard

def test_coding_agent_router_routes_correctly():
    scoreboard = AgentScoreboard()
    router = CodingAgentRouter(scoreboard)
    
    res = router.route_defect("frontend UI fix")
    assert res["assigned_agent"] == "Claude Code"
    assert res["sandbox_required"] is True

    res2 = router.route_defect("backend API fix")
    assert res2["assigned_agent"] == "Claude Code"
    assert res2["sandbox_required"] is True
