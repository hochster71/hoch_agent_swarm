import os
from backend.runtime_process import RuntimeProcessBus, RuntimeProcessType, RuntimeProcessState

def test_runtime_process_bus_emit_and_tail(tmp_path):
    log_file = tmp_path / "test_events.jsonl"
    bus = RuntimeProcessBus(path=str(log_file))
    
    # Emit an event
    event = bus.emit(
        process_type=RuntimeProcessType.AGENT_TASK,
        state=RuntimeProcessState.RUNNING,
        message="Running test agent task",
        agent_id="test-agent",
        task_id="test-task",
        provider="ollama",
        model="llama3",
        confidence_score=0.85
    )
    
    assert event.event_id is not None
    assert event.process_type == "AGENT_TASK"
    assert event.state == "RUNNING"
    assert event.agent_id == "test-agent"
    assert event.task_id == "test-task"
    assert event.provider == "ollama"
    assert event.model == "llama3"
    assert event.confidence_score == 0.85
    
    # Assert written file
    assert log_file.exists()
    lines = log_file.read_text().splitlines()
    assert len(lines) == 1
    
    # Tail the bus
    tailed = bus.tail(limit=5)
    assert len(tailed) == 1
    assert tailed[0]["event_id"] == event.event_id
    assert tailed[0]["message"] == "Running test agent task"
