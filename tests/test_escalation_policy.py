from backend.model_router import escalation_policy

def test_escalation_policy_defaults():
    # Escalation must be disabled by default
    res = escalation_policy.check_escalation_policy("general", "hello")
    assert res["allowed"] is False
    assert res["recommended"] is False
    assert "disabled" in res["reason"]

def test_blocked_task_types():
    # Prohibited task types must be blocked
    res = escalation_policy.check_escalation_policy("money_movement", "send money")
    assert res["allowed"] is False
    assert "disabled" in res["reason"] or "prohibited" in res["reason"]

def test_high_risk_keywords():
    # Keywords check
    res = escalation_policy.check_escalation_policy("general", "delete database credentials")
    # Even if escalation is disabled, allowed should be False
    assert res["allowed"] is False
