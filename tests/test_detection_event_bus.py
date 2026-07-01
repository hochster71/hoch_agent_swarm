import os
import tempfile
from pathlib import Path
import pytest
from backend.detection_events import DetectionEventBus, DetectionEvent

def test_detection_event_bus_writes_jsonl():
    with tempfile.TemporaryDirectory() as tmpdir:
        events_file = Path(tmpdir) / "test_events.jsonl"
        # Create bus targeting temp file
        bus = DetectionEventBus(path=str(events_file))
        
        # Emit an event
        event = bus.emit(
            event_family="TEST_FAMILY",
            severity="medium",
            source_log="test_source",
            actor="test-actor",
            verdict="ALLOWED",
            reason="just testing"
        )
        
        assert events_file.exists()
        lines = events_file.read_text().splitlines()
        assert len(lines) == 1
        
        # Verify tail
        events = bus.tail(limit=10)
        assert len(events) == 1
        assert events[0]["event_family"] == "TEST_FAMILY"
        assert events[0]["severity"] == "medium"
        assert events[0]["event_id"] == event.event_id
