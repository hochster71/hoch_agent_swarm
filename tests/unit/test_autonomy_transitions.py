import pytest
from backend.brain.orchestrator import BrainOrchestrator
from backend.brain.database import init_brain_tables

def test_mode_transitions():
    init_brain_tables()
    orchestrator = BrainOrchestrator()
    
    # Switch to suggest (allowed)
    assert orchestrator.set_mode("suggest") is True
    assert orchestrator.mode == "suggest"
    
    # Switch to shadow (allowed)
    assert orchestrator.set_mode("shadow") is True
    assert orchestrator.mode == "shadow"
    
    # Switch to autonomous should fail because readiness score is default/below gate (90%)
    assert orchestrator.set_mode("autonomous") is False
