import pytest
from backend.brain.orchestrator import BrainOrchestrator
from backend.brain.database import init_brain_tables, get_db_connection

def test_rejection_reduces_confidence(monkeypatch):
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
    
    # 1. Trigger suggestion recommendation
    status = orchestrator.suggest_next_action()
    sug = status["activeSuggestion"]
    assert sug is not None
    
    # 2. Get initial confidence
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT confidence FROM brain_suggestions WHERE id = ?", (sug["id"],))
    initial_confidence = cursor.fetchone()[0]
    conn.close()
    
    # 3. Reject suggestion
    orchestrator.submit_feedback(sug["id"], "rejected", "Vague recommendations")
    
    # 4. Check confidence reduced
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT confidence FROM brain_suggestions WHERE id = ?", (sug["id"],))
    final_confidence = cursor.fetchone()[0]
    conn.close()
    
    assert final_confidence < initial_confidence
