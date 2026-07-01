from backend.promptops.prompt_scorecard import PromptScorecard

def test_prompt_scorecard():
    scorecard = PromptScorecard()
    
    # Evaluate a weak prompt
    weak_res = scorecard.evaluate("Build HAS e2e production ready no errors")
    assert weak_res["score"] < 60
    assert weak_res["status"] == "BLOCKED_UNTIL_SCOPED"
    
    # Evaluate a strong prompt
    strong_res = scorecard.evaluate(
        "Fix Docker UI truth mismatch, prove API/UI BLOCKED/50.0, run docker_truth_check "
        "affecting backend/main.py, docs/evidence, config/autonomy_policy.yaml. "
        "Non-goals: do not modify frontend components. Rollback: stop if pytest fails."
    )
    assert strong_res["score"] >= 80
    assert strong_res["status"] == "EXECUTABLE"
