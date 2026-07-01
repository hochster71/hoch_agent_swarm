import os
import tempfile
from backend.meta_orchestrator.decision_queue import DecisionQueue

def test_decision_queue_adds_and_resolves_decisions():
    # Use temporary file database
    fd, temp_db = tempfile.mkstemp()
    try:
        dq = DecisionQueue(temp_db)
        
        # Add a decision
        dq.add_decision("test_1", "Test Title", "Test Desc", "test_domain", "CRITICAL")
        
        pending = dq.get_pending_decisions()
        assert len(pending) == 1
        assert pending[0]["decision_id"] == "test_1"
        assert pending[0]["severity"] == "CRITICAL"
        
        # Load score calculation
        assert dq.compute_orchestration_load() == 10.0
        
        # Resolve decision
        dq.resolve_decision("test_1", "Resolved via unit test")
        assert len(dq.get_pending_decisions()) == 0
        assert dq.compute_orchestration_load() == 0.0
    finally:
        os.close(fd)
        os.unlink(temp_db)
