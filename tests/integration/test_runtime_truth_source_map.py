import sqlite3
from backend.runtime_truth.state_store import DB_PATH, init_runtime_truth_tables

def test_source_map_records():
    init_runtime_truth_tables()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Ensure tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='source_map'")
    row = cursor.fetchone()
    assert row is not None
    conn.close()
