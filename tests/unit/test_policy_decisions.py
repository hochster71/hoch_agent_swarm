import pytest
from backend.brain.autonomy_policy import AutonomyPolicy

def test_policy_decisions():
    policy = AutonomyPolicy()
    
    # Check allowed actions
    allowed, req_app, desc = policy.is_action_allowed("read_files")
    assert allowed is True
    assert req_app is False
    
    # Check blocked actions
    allowed, req_app, desc = policy.is_action_allowed("production_release")
    assert allowed is False
    assert req_app is True
    
    # Check unknown action (should fail closed)
    allowed, req_app, desc = policy.is_action_allowed("unregistered_bad_action")
    assert allowed is False
    assert req_app is True
