import pytest
from backend.brain.orchestrator import BrainOrchestrator
from backend.brain.database import init_brain_tables

def test_chat_feedback_doctrine_flow(monkeypatch):
    init_brain_tables()
    orchestrator = BrainOrchestrator()
    
    # Mock get_next_pert_task to ensure there is a task to suggest
    monkeypatch.setattr(orchestrator.queue, "get_next_pert_task", lambda: {
        "id": "A",
        "name": "Verify build health",
        "owner": "qa-agent",
        "critical": True
    })
    
    session_id = orchestrator.chat.get_or_create_active_session()
    
    # 1. Add user chat message
    orchestrator.chat.add_message(session_id, "user", "Please verify build health.")
    
    # 2. Trigger suggestion recommendation
    status = orchestrator.suggest_next_action()
    sug = status["activeSuggestion"]
    assert sug is not None
    
    # 3. Submit reject feedback with correction
    feedback_status = orchestrator.submit_feedback(sug["id"], "rejected", "Always double check the docker service states")
    
    # 4. Assert new rule is learned from the correction
    rules = feedback_status["doctrineRules"]
    assert any("Avoid action: Always double check the docker service states" in r["ruleText"] for r in rules)
