import sqlite3
import pytest
from backend.runtime_truth.state_store import DB_PATH
from backend.final_verifier.blocker_reporter import BlockerReporter

def test_meta_orchestrator_blockers():
    reporter = BlockerReporter(db_path=DB_PATH)
    res = reporter.get_active_blockers()
    assert "blockers" in res
    assert isinstance(res["blockers"], list)
