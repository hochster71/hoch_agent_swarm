import pytest
from backend.coding_control_plane.tool_registry import ToolRegistry

def test_tool_detection_checks():
    registry = ToolRegistry()
    tools = registry.get_registered_tools()
    
    # Assert we have tools mapped
    assert len(tools) > 0
    
    # Check that we verified installed vs missing
    for t in tools:
        assert "tool" in t
        assert "configured" in t
        assert "installed" in t
        assert "status" in t
        assert t["status"] in ["installed", "missing", "configured_only", "simulated", "unavailable"]
