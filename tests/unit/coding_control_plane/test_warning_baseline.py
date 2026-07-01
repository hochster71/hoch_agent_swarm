from backend.coding_control_plane.warning_baseline import WarningBaselineManager

def test_warning_baseline_legacy():
    manager = WarningBaselineManager()
    
    # Existing baseline warning
    res = manager.evaluate_warning("datetime.datetime.utcnow() is deprecated and scheduled for removal")
    assert res["status"] == "BASELINED_OWNED"
    assert res["is_new"] is False
    assert res["owner"] == "Refactor Agent"

def test_warning_baseline_new():
    manager = WarningBaselineManager()
    
    # A completely new warning
    res = manager.evaluate_warning("Some random unexpected deprecation warning message here")
    assert res["status"] == "NEW_BLOCKING"
    assert res["is_new"] is True
    assert res["is_blocking"] is True
