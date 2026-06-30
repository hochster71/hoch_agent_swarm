import sqlite3
import pytest
from datetime import datetime, timezone, timedelta
from backend.runtime_truth.state_store import DB_PATH, now_iso
from backend.runtime_truth.go_nogo_manager import GoNoGoManager

@pytest.fixture
def clean_db():
    # Insert clean test signals
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("DELETE FROM runtime_truth_signals WHERE signal_id IN ('production_go_status', 'production_nogo_status', 'go_nogo_contradiction_status', 'go_signal_source_count', 'no_go_signal_source_count', 'stale_go_signal_count', 'active_release_go_status', 'release_go_source')")
        conn.commit()
    finally:
        conn.close()

def test_go_nogo_classification(clean_db):
    manager = GoNoGoManager()
    
    # 1. Insert stale GO test signal and valid NO-GO test signal
    now = datetime.now(timezone.utc)
    stale_time = (now - timedelta(seconds=600)).isoformat()
    fresh_time = now.isoformat()
    
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("""
            INSERT INTO runtime_truth_signals
            (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence)
            VALUES ('production_go_status', 'Go', 'GO', 'test', 'test', ?, 60, 'fresh', 1.0)
        """, (stale_time,))
        conn.execute("""
            INSERT INTO runtime_truth_signals
            (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence)
            VALUES ('production_nogo_status', 'NoGo', 'NO-GO', 'computed', 'system', ?, 60, 'fresh', 1.0)
        """, (fresh_time,))
        conn.commit()
    finally:
        conn.close()
        
    # 2. Get sources and assert classification
    sources = manager.get_sources()
    go_src = next(s for s in sources if s["signal_id"] == "production_go_status")
    nogo_src = next(s for s in sources if s["signal_id"] == "production_nogo_status")
    
    assert go_src["active"] is False
    assert go_src["classification"] == "test"
    
    assert nogo_src["active"] is True
    assert nogo_src["classification"] == "computed"
    
    # 3. Process and update
    res = manager.process_and_update()
    assert res["contradiction_status"] == "INACTIVE"
    assert res["active_go_count"] == 0
    assert res["active_nogo_count"] == 1
    assert res["stale_go_count"] == 1
    assert res["release_go_status"] == "NO-GO"

def test_stale_go_stale_nogo(clean_db):
    manager = GoNoGoManager()
    
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("""
            INSERT INTO runtime_truth_signals
            (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence)
            VALUES ('production_go_status', 'Go', 'GO', 'test', 'test', '2026-06-29T12:00:00Z', 60, 'fresh', 1.0)
        """)
        conn.execute("""
            INSERT INTO runtime_truth_signals
            (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence)
            VALUES ('production_nogo_status', 'NoGo', 'NO-GO', 'test', 'test', '2026-06-29T12:00:00Z', 60, 'fresh', 1.0)
        """)
        conn.commit()
    finally:
        conn.close()

    res = manager.process_and_update()
    assert res["contradiction_status"] == "INACTIVE"

    from backend.final_verifier.contradiction_checker import ContradictionChecker
    from backend.final_verifier.readiness_cap_engine import ReadinessCapEngine
    from backend.final_verifier.final_verdict import FinalVerdict

    checker = ContradictionChecker()
    cc_res = checker.check_contradictions()
    assert cc_res["is_valid"] is True

    engine = ReadinessCapEngine()
    caps_res = engine.calculate_caps()
    assert not any(c == "GO/NO-GO contradiction active" for c in caps_res["caps"])
    assert any(c == "No active release GO source" for c in caps_res["caps"])
    assert caps_res["score"] <= 50.0

    verdict_engine = FinalVerdict()
    verdict = verdict_engine.get_final_verdict()
    blockers = verdict["blocker_reporter"]["blockers"]
    assert not any(b["type"] == "GO_NO_GO_CONTRADICTION" for b in blockers)
    assert any(b["type"] == "NO_ACTIVE_RELEASE_GO" for b in blockers)
    assert verdict["status"] == "BLOCKED"

def test_valid_release_go(clean_db):
    manager = GoNoGoManager()
    now_str = now_iso()
    
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("""
            INSERT INTO runtime_truth_signals
            (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence)
            VALUES ('production_go_status', 'Go', 'GO', 'manual', 'user', ?, 60, 'fresh', 1.0)
        """, (now_str,))
        conn.commit()
    finally:
        conn.close()

    res = manager.process_and_update()
    assert res["contradiction_status"] == "INACTIVE"
    assert res["release_go_status"] == "GO"

    from backend.final_verifier.contradiction_checker import ContradictionChecker
    from backend.final_verifier.readiness_cap_engine import ReadinessCapEngine
    from backend.final_verifier.final_verdict import FinalVerdict

    checker = ContradictionChecker()
    cc_res = checker.check_contradictions()
    assert cc_res["is_valid"] is True

    engine = ReadinessCapEngine()
    caps_res = engine.calculate_caps()
    assert not any(c == "GO/NO-GO contradiction active" for c in caps_res["caps"])
    assert not any(c == "No active release GO source" for c in caps_res["caps"])

    verdict_engine = FinalVerdict()
    verdict = verdict_engine.get_final_verdict()
    blockers = verdict["blocker_reporter"]["blockers"]
    assert not any(b["type"] == "GO_NO_GO_CONTRADICTION" for b in blockers)
    assert not any(b["type"] == "NO_ACTIVE_RELEASE_GO" for b in blockers)

def test_active_go_active_nogo(clean_db):
    manager = GoNoGoManager()
    now_str = now_iso()
    
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("""
            INSERT INTO runtime_truth_signals
            (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence)
            VALUES ('production_go_status', 'Go', 'GO', 'manual', 'user', ?, 60, 'fresh', 1.0)
        """, (now_str,))
        conn.execute("""
            INSERT INTO runtime_truth_signals
            (signal_id, name, value, source, source_type, last_updated, ttl_seconds, freshness, confidence)
            VALUES ('production_nogo_status', 'NoGo', 'NO-GO', 'computed', 'system', ?, 60, 'fresh', 1.0)
        """, (now_str,))
        conn.commit()
    finally:
        conn.close()

    res = manager.process_and_update()
    assert res["contradiction_status"] == "ACTIVE"

    from backend.final_verifier.contradiction_checker import ContradictionChecker
    from backend.final_verifier.readiness_cap_engine import ReadinessCapEngine
    from backend.final_verifier.final_verdict import FinalVerdict

    checker = ContradictionChecker()
    cc_res = checker.check_contradictions()
    assert cc_res["is_valid"] is False

    engine = ReadinessCapEngine()
    caps_res = engine.calculate_caps()
    assert any(c == "GO/NO-GO contradiction active" for c in caps_res["caps"])

    verdict_engine = FinalVerdict()
    verdict = verdict_engine.get_final_verdict()
    blockers = verdict["blocker_reporter"]["blockers"]
    assert any(b["type"] == "GO_NO_GO_CONTRADICTION" for b in blockers)
