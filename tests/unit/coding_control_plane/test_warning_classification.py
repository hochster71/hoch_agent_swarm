import pytest
from backend.coding_control_plane.warning_baseline import WarningBaselineManager

def test_warning_classification_categories():
    manager = WarningBaselineManager()
    
    # 1. False positive stub
    res1 = manager.evaluate_warning("Mock warning inside a unit test stub")
    assert res1["status"] == "FALSE_POSITIVE"
    assert res1["is_blocking"] is False

    # 2. Baselined/owned
    res2 = manager.evaluate_warning("DeprecationWarning: datetime.datetime.utcnow() is deprecated")
    assert res2["status"] == "BASELINED_OWNED"
    assert res2["is_blocking"] is False

    # 3. New blocking warning
    res3 = manager.evaluate_warning("DeprecationWarning: a new deprecation pattern detected")
    assert res3["status"] == "NEW_BLOCKING"
    assert res3["is_blocking"] is True

    # 4. Unknown warning
    res4 = manager.evaluate_warning("an unknown obscure warning message")
    assert res4["status"] == "UNKNOWN_BLOCKING"
    assert res4["is_blocking"] is True
