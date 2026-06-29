from backend.coding_control_plane.warning_baseline import WarningBaselineManager

def test_warning_baseline_legacy():
    manager = WarningBaselineManager()
    
    # Existing baseline warning
    res = manager.evaluate_warning("datetime.datetime.utcnow() is deprecated and scheduled for removal")
    assert res["status"] == "LEGACY_DEBT"
    assert res["is_new"] is False
    assert res["owner"] == "Refactor Agent"

def test_warning_baseline_new():
    manager = WarningBaselineManager()
    
    # A completely new warning
    res = manager.evaluate_warning("Some random unexpected compiler warning message here")
    assert res["status"] == "NEW_WARNING_FAIL"
    assert res["is_new"] is True
