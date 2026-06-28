"""
tests/test_swarm_pipeline.py

Unit tests for database helper methods and functions in run_batch_swarm_analysis.py:
- get_eligible_diagrams
- update_diagram_record
- parse_audit_verdict
- calculate_quality_score

Uses a temporary test database to ensure the production database is not modified or polluted.
"""

import os
import sqlite3
import json
from datetime import datetime, timedelta
import pytest

import run_batch_swarm_analysis

@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Fixture to set up a temporary SQLite database with the diagrams table schema."""
    db_file = tmp_path / "test_cybersecurity_diagrams.db"
    # Monkeypatch the DB_PATH global in run_batch_swarm_analysis to target our test db
    monkeypatch.setattr(run_batch_swarm_analysis, "DB_PATH", str(db_file))
    
    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE diagrams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            source TEXT NOT NULL,
            description TEXT,
            architecture_type TEXT,
            components TEXT,
            threat_vectors TEXT,
            mitigations TEXT,
            status TEXT DEFAULT 'PENDING',
            analyzed_at TIMESTAMP,
            quality_score REAL,
            artifact_links TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    return db_file


def test_calculate_quality_score(tmp_path):
    """Test calculate_quality_score behavior and calculation rules."""
    # Case 1: validation_passed = False -> score is 0.0
    assert run_batch_swarm_analysis.calculate_quality_score(False, "any_path", "any_path") == 0.0
    
    # Case 2: validation_passed = True, both files are missing -> base score of 50.0
    assert run_batch_swarm_analysis.calculate_quality_score(True, "missing_audit.md", "missing_plan.md") == 50.0
    
    # Case 3: validation_passed = True, files exist with specific sizes
    audit_file = tmp_path / "audit.md"
    # Write 500 bytes (min(25.0, 500 / 100.0) = 5.0 pts)
    audit_file.write_text("a" * 500)
    
    plan_file = tmp_path / "plan.md"
    # Write 1500 bytes (min(25.0, 1500 / 150.0) = 10.0 pts)
    plan_file.write_text("b" * 1500)
    
    # Total score: 50.0 + 5.0 + 10.0 = 65.0
    score = run_batch_swarm_analysis.calculate_quality_score(True, str(audit_file), str(plan_file))
    assert score == 65.0
    
    # Case 4: Capped at 100.0 max
    large_audit = tmp_path / "large_audit.md"
    large_audit.write_text("a" * 5000)  # max contribution 25.0
    large_plan = tmp_path / "large_plan.md"
    large_plan.write_text("b" * 5000)  # max contribution 25.0
    
    score_max = run_batch_swarm_analysis.calculate_quality_score(True, str(large_audit), str(large_plan))
    assert score_max == 100.0


def test_parse_audit_verdict(tmp_path):
    """Test parsing the verdict from a security audit report."""
    # Case 1: Missing file -> FAILED
    assert run_batch_swarm_analysis.parse_audit_verdict("non_existent_file.md") == "FAILED"
    
    # Case 2: File exists but no ## Verdict section -> FAILED
    no_verdict_file = tmp_path / "no_verdict.md"
    no_verdict_file.write_text("# Report\n\nSome content without a verdict section.")
    assert run_batch_swarm_analysis.parse_audit_verdict(str(no_verdict_file)) == "FAILED"
    
    # Case 3: Verdict is COMPLIANT or PASS -> COMPLIANT
    compliant_file = tmp_path / "compliant.md"
    compliant_file.write_text("# Report\n\n## Verdict\n\nThe configuration is COMPLIANT.")
    assert run_batch_swarm_analysis.parse_audit_verdict(str(compliant_file)) == "COMPLIANT"
    
    pass_file = tmp_path / "pass.md"
    pass_file.write_text("# Report\n\n## Verdict\n\nPASS - All checks met.")
    assert run_batch_swarm_analysis.parse_audit_verdict(str(pass_file)) == "COMPLIANT"
    
    # Case 4: Verdict is NON-COMPLIANT or FAIL -> NON-COMPLIANT
    non_compliant_file = tmp_path / "non_compliant.md"
    non_compliant_file.write_text("# Report\n\n## Verdict\n\nNON-COMPLIANT configuration.")
    assert run_batch_swarm_analysis.parse_audit_verdict(str(non_compliant_file)) == "NON-COMPLIANT"
    
    fail_file = tmp_path / "fail.md"
    fail_file.write_text("# Report\n\n## Verdict\n\nFAIL. Did not meet standard.")
    assert run_batch_swarm_analysis.parse_audit_verdict(str(fail_file)) == "NON-COMPLIANT"
    
    # Case 5: Default fallback (verdict section exists but none of the words match) -> COMPLIANT
    fallback_file = tmp_path / "fallback.md"
    fallback_file.write_text("# Report\n\n## Verdict\n\nUNKNOWN verdict here.")
    assert run_batch_swarm_analysis.parse_audit_verdict(str(fallback_file)) == "COMPLIANT"


def test_update_diagram_record(temp_db):
    """Test update_diagram_record accurately updates a row with JSON and timestamps."""
    # Insert a dummy record first
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO diagrams (title, source, description, status)
        VALUES ('Test Title', 'Test Source', 'Test Description', 'PENDING')
    """)
    diagram_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # Update it
    mitigations = "Suggested mitigations list"
    status = "COMPLIANT"
    quality_score = 85.5
    artifact_links = {"audit.md": "/path/to/audit.md", "plan.md": "/path/to/plan.md"}
    
    run_batch_swarm_analysis.update_diagram_record(
        diagram_id=diagram_id,
        mitigations=mitigations,
        status=status,
        quality_score=quality_score,
        artifact_links=artifact_links
    )
    
    # Verify updates
    conn = sqlite3.connect(str(temp_db))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM diagrams WHERE id = ?", (diagram_id,))
    row = cursor.fetchone()
    conn.close()
    
    assert row is not None
    assert row["mitigations"] == mitigations
    assert row["status"] == status
    assert row["quality_score"] == quality_score
    assert json.loads(row["artifact_links"]) == artifact_links
    assert row["analyzed_at"] is not None
    # Check that analyzed_at is a valid ISO format datetime
    dt = datetime.fromisoformat(row["analyzed_at"])
    assert isinstance(dt, datetime)


def test_get_eligible_diagrams(temp_db):
    """Test get_eligible_diagrams correctly filters eligible vs non-eligible rows based on conditions."""
    now = datetime.now()
    
    test_data = [
        # Title, Source, Desc, Status, Mitigations, Analyzed_at
        # Eligible cases:
        ("Null Status", "Source", "Desc", None, "Mitigations", None),
        ("Pending Status", "Source", "Desc", "PENDING", "Mitigations", None),
        ("Failed Status", "Source", "Desc", "FAILED", "Mitigations", None),
        ("Non-Compliant Status", "Source", "Desc", "NON-COMPLIANT", "Mitigations", None),
        ("Null Mitigations", "Source", "Desc", "COMPLIANT", None, now.isoformat()),
        ("Empty Mitigations", "Source", "Desc", "COMPLIANT", "", now.isoformat()),
        ("Spaces Mitigations", "Source", "Desc", "COMPLIANT", "   ", now.isoformat()),
        ("Null Analyzed At", "Source", "Desc", "COMPLIANT", "Mitigations", None),
        ("Stale Analyzed At", "Source", "Desc", "COMPLIANT", "Mitigations", (now - timedelta(hours=30)).isoformat()),
        # Non-eligible cases:
        ("Fresh Compliant", "Source", "Desc", "COMPLIANT", "Mitigations", (now - timedelta(hours=2)).isoformat()),
    ]
    
    conn = sqlite3.connect(str(temp_db))
    cursor = conn.cursor()
    for title, source, description, status, mitigations, analyzed_at in test_data:
        cursor.execute("""
            INSERT INTO diagrams (title, source, description, status, mitigations, analyzed_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (title, source, description, status, mitigations, analyzed_at))
    conn.commit()
    conn.close()
    
    # We expect 9 of the 10 diagrams to be eligible
    eligible = run_batch_swarm_analysis.get_eligible_diagrams(max_items=20, stale_hours=24)
    assert len(eligible) == 9
    
    # Verify titles of the eligible ones (should exclude "Fresh Compliant")
    eligible_titles = [row["title"] for row in eligible]
    assert "Fresh Compliant" not in eligible_titles
    assert "Null Status" in eligible_titles
    assert "Stale Analyzed At" in eligible_titles
    
    # Test max_items limit
    limited = run_batch_swarm_analysis.get_eligible_diagrams(max_items=3, stale_hours=24)
    assert len(limited) == 3
