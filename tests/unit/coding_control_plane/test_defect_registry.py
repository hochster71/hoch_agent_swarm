import sqlite3
import pytest
from backend.runtime_truth.state_store import DB_PATH
from backend.coding_control_plane.defect_registry import DefectRegistry

def test_defect_registry_lifecycle():
    reg = DefectRegistry(db_path=DB_PATH)
    
    # Register defect
    defect = reg.register_defect("test_reg_1", "syntax error", "CRITICAL", "backend", "test_file.py")
    assert defect["defect_id"] == "test_reg_1"
    assert defect["severity"] == "CRITICAL"
    assert defect["status"] == "OPEN"

    # Get defects
    defects = reg.get_defects()
    assert any(d["defect_id"] == "test_reg_1" for d in defects)

    # Clean up
    with sqlite3.connect(DB_PATH, timeout=60) as conn:
        conn.execute("DELETE FROM coding_defects WHERE defect_id = 'test_reg_1'")
        conn.commit()
