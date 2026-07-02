import pytest
from backend.michael_ai.synthesizer import synthesize_current_state, seed_initial_truths

def test_current_state_synthesis_includes_accepted_truths():
    # Make sure seeded truths are initialized
    seed_initial_truths()
    
    state = synthesize_current_state()
    assert state["operator"] == "Michael Hoch"
    assert len(state["accepted_truths"]) > 0
    
    # Check key seed truths
    truths_str = " ".join(state["accepted_truths"])
    assert "HOCH-200" in truths_str
    assert "50.116.41.183" in truths_str
    assert "100.87.18.15" in truths_str
    assert "3012" in truths_str
    assert "running and healthy" in truths_str

def test_local_ui_cleanup_is_not_priority_when_evidence_pending():
    state = synthesize_current_state()
    # Confirm local UI cleanup is not the active priority when evidence locks are pending
    assert "Local UI cleanup" not in state["active_priority"]
    assert "ui-polish" not in state["active_priority"].lower()
    
    # Assert avoid lessons contain UI polish warnings
    avoid_list = " ".join(state["do_not_do"]).lower()
    assert "ui polish" in avoid_list or "decorative" in avoid_list
