from unittest.mock import patch, MagicMock
from backend.main import get_runtime_process_animation_state_endpoint

def test_get_runtime_process_animation_state_mapping():
    # Mock runtime process bus tail to return a specific list of events
    with patch("backend.runtime_process.RuntimeProcessBus.tail") as mock_tail:
        mock_tail.return_value = [
            {
                "event_id": "ev-1",
                "process_type": "LOCAL_MODEL_HEALTH",
                "state": "LIVE",
                "provider": "ollama",
                "model": "llama3",
                "confidence_score": None,
                "requires_approval": False,
                "escalation_used": False,
                "message": "Health OK"
            },
            {
                "event_id": "ev-2",
                "process_type": "LOCAL_ARBITRATION",
                "state": "ARBITRATING",
                "provider": None,
                "model": None,
                "confidence_score": None,
                "requires_approval": False,
                "escalation_used": False,
                "message": "Arbitrating locally"
            },
            {
                "event_id": "ev-3",
                "process_type": "GOOGLE_FRONTIER_CALL",
                "state": "RUNNING",
                "provider": "google_gemini",
                "model": "gemini-3.1-flash-lite",
                "confidence_score": None,
                "requires_approval": True,
                "escalation_used": True,
                "message": "Calling Google Frontier"
            }
        ]
        
        response = get_runtime_process_animation_state_endpoint()
        
        assert response["truth"] == "LIVE"
        assert response["animation_mode"] == "runtime_process"
        assert len(response["processes"]) == 3
        
        # Check first event (LOCAL_MODEL_HEALTH / LIVE) mapping
        p1 = response["processes"][0]
        assert p1["event_id"] == "ev-1"
        assert p1["visual"]["color"] == "green"
        assert p1["visual"]["motion"] == "heartbeat"
        assert p1["visual"]["pulse"] is True
        
        # Check second event (LOCAL_ARBITRATION) mapping
        p2 = response["processes"][1]
        assert p2["event_id"] == "ev-2"
        assert p2["visual"]["color"] == "cyan"
        assert p2["visual"]["motion"] == "orbit"
        
        # Check third event (GOOGLE_FRONTIER_CALL / RUNNING) mapping
        p3 = response["processes"][2]
        assert p3["event_id"] == "ev-3"
        assert p3["visual"]["color"] == "purple"
        assert p3["visual"]["motion"] == "stream"
        assert p3["visual"]["trail"] == "google"
        assert p3["visual"]["speed"] == "fast"
