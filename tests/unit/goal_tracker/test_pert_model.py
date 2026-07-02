from backend.goal_tracker.pert_model import get_goal_pert_analysis, calculate_pert_estimates

def test_pert_estimates_calculation():
    # Test a simple mock lane estimation
    mock_lanes = [{
        "optimistic_minutes": 10,
        "most_likely_minutes": 20,
        "pessimistic_minutes": 30
    }]
    res = calculate_pert_estimates(mock_lanes)
    # Expected: (10 + 4*20 + 30)/6 = 120/6 = 20.0
    assert res[0]["expected_minutes"] == 20.0
    # Variance: ((30 - 10)/6)**2 = (20/6)**2 = 3.33**2 = 11.11
    assert abs(res[0]["variance"] - 11.11) < 0.05

def test_goal_pert_analysis():
    analysis = get_goal_pert_analysis()
    
    assert analysis["goal_id"] == "HAS-HASF-GOAL"
    assert analysis["goal_name"] == "/GOAL"
    assert analysis["status"] == "NO-GO"
    assert analysis["final_verifier"] == "BLOCKED"
    assert analysis["readiness_score"] == 50
    assert "NO_ACTIVE_RELEASE_GO" in analysis["active_blockers"]
    
    # Critical path sums to exactly 600.0 minutes
    assert analysis["expected_completion_minutes"] == 600.0
    
    # Verify HELM is mapped
    helm_lane = next(l for l in analysis["lanes"] if l["id"] == "A")
    assert helm_lane["owner_agent"] == "HELM"
