# -*- coding: utf-8 -*-
"""
tests/test_brain_runtime.py — Pytest suite for BRAIN2 features.
"""

import json
import sqlite3
from pathlib import Path
import pytest

from hoch_agent_swarm.brain_runtime import (
    BrainRuntime,
    get_brain_runtime,
    tokenize
)

def test_brain_runtime_singleton():
    br1 = get_brain_runtime()
    br2 = get_brain_runtime()
    assert br1 is br2

def test_tokenization_helper():
    text = "The quick brown fox jumps over the lazy dog and or with"
    tokens = tokenize(text)
    # Stop words like 'The', 'and', 'or', 'with' should be removed
    assert "the" not in tokens
    assert "and" not in tokens
    assert "or" not in tokens
    assert "with" not in tokens
    assert "fox" in tokens
    assert "lazy" in tokens

def test_sqlite_tables_created(tmp_path):
    db_file = tmp_path / "test_brain.db"
    br = BrainRuntime()
    # Temporarily point connection to test DB
    br.db_path = db_file
    br.conn = sqlite3.connect(str(db_file))
    br.initialize_db()

    cursor = br.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r["name"] for r in cursor.fetchall()]
    assert "evidence_nodes" in tables
    assert "graph_edges" in tables

def test_markdown_chunker():
    br = get_brain_runtime()
    md_content = """# Heading 1
Some body text under heading 1.
## Subheading 1.1
Subheading text here.
# Heading 2
Heading 2 body content."""
    
    chunks = br._chunk_markdown(md_content)
    assert len(chunks) == 3
    assert chunks[0][0] == "Heading 1"
    assert "Some body text" in chunks[0][1]
    assert chunks[1][0] == "Subheading 1.1"
    assert "Subheading text" in chunks[1][1]
    assert chunks[2][0] == "Heading 2"
    assert "Heading 2 body" in chunks[2][1]

def test_trust_scoring():
    br = get_brain_runtime()
    # Base draft
    score_draft = br._calculate_trust_score("artifacts/test.md", "draft content", has_git=False)
    assert score_draft == 70.0

    # Git signature boost
    score_git = br._calculate_trust_score("artifacts/test.md", "draft content", has_git=True)
    assert score_git == 80.0

    # Security report and git signature boost
    score_audit = br._calculate_trust_score("artifacts/security_reviews/security_audit_report.md", "facts observed", has_git=True)
    assert score_audit == 100.0  # 70 + 10 (git) + 15 (audit report) + 5 (facts observed keyword) = 100

def test_tf_idf_query_matching(tmp_path):
    db_file = tmp_path / "test_query.db"
    br = BrainRuntime()
    br.db_path = db_file
    br.conn = sqlite3.connect(str(db_file))
    br.conn.row_factory = sqlite3.Row
    br.initialize_db()

    # Populate dummy evidence chunks
    cursor = br.conn.cursor()
    cursor.execute("""
        INSERT INTO evidence_nodes (id, path, chunk_index, content, trust_score, timestamp, commit_sha, author, metadata)
        VALUES 
        ('node-1', 'artifacts/doc1.md', 0, 'Continuous Monitoring framework and security control audits', 85, '2026-06-28', 'sha1', 'author1', '{}'),
        ('node-2', 'artifacts/doc2.md', 0, 'Database credentials and firewall configuration logs', 75, '2026-06-28', 'sha2', 'author2', '{}'),
        ('node-3', 'artifacts/doc3.md', 0, 'Vulnerability scan outcomes and SAST report findings', 90, '2026-06-28', 'sha3', 'author3', '{}')
    """)
    br.conn.commit()

    # Search for Continuous Monitoring
    results = br.query_evidence("Continuous Monitoring", limit=5)
    assert len(results) > 0
    assert results[0]["id"] == "node-1"
    assert results[0]["relevance_score"] > 0.0

    # Search with min_trust
    results_trust = br.query_evidence("Continuous Monitoring", limit=5, min_trust=90)
    assert len(results_trust) == 0  # node-1 is trust 85

def test_validation_gap_closures(tmp_path):
    db_file = tmp_path / "test_closures.db"
    br = BrainRuntime()
    br.db_path = db_file
    br.conn = sqlite3.connect(str(db_file))
    br.conn.row_factory = sqlite3.Row
    br.initialize_db()

    cursor = br.conn.cursor()
    # Insert node that matches a prompt gap with 'verdict: pass'
    cursor.execute("""
        INSERT INTO evidence_nodes (id, path, chunk_index, content, trust_score, timestamp, commit_sha, author, metadata)
        VALUES 
        ('node-1', 'artifacts/security_reviews/security_audit_report.md', 0, 'Audit verification for BRAIN-001 with decision: pass', 95, '2026-06-28', 'sha1', 'author1', '{}')
    """)
    br.conn.commit()

    res = br.validate_gap_closures()
    assert res["status"] == "AUDITED"
    # Find BRAIN-001 gap closure
    closures = res["closures"]
    brain_closure = next((c for c in closures if c["missing_prompt_id"] == "BRAIN-001"), None)
    assert brain_closure is not None
    assert brain_closure["status"] == "RESOLVED"
    assert brain_closure["resolved_by_node"] == "node-1"

def test_brain_flask_apis():
    from hoch_agent_swarm.ui_server import app
    app.config["TESTING"] = True
    with app.test_client() as c:
        # Ingestion run
        r = c.post("/api/v1/brain/ingest")
        assert r.status_code == 200
        data = r.get_json()
        assert data["status"] == "SUCCESS"

        # Search Query
        r = c.get("/api/v1/brain/query?query=Continuous%20Monitoring")
        assert r.status_code == 200

        # Graph Edge/Node Retrieval
        r = c.get("/api/v1/brain/graph")
        assert r.status_code == 200
        data = r.get_json()
        assert "nodes" in data
        assert "edges" in data

        # Validation status list
        r = c.get("/api/v1/brain/validation-status")
        assert r.status_code == 200
        data = r.get_json()
        assert data["status"] == "AUDITED"
