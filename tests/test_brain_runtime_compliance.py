# -*- coding: utf-8 -*-
"""
tests/test_brain_runtime_compliance.py — Pytest suite for BRAIN3.
"""

import os
import json
import zipfile
import io
from pathlib import Path
import pytest
from flask.testing import FlaskClient

from hoch_agent_swarm.brain_runtime import get_brain_runtime, DB_PATH
from hoch_agent_swarm.promptbrain_manager import get_promptbrain_manager
from hoch_agent_swarm.promptqa_manager import get_promptqa_manager
from hoch_agent_swarm.ui_server import app

def test_promptqa_json_chunked_ingestion():
    runtime = get_brain_runtime()
    
    # Trigger ingestion
    ingest_res = runtime.ingest_artifacts()
    assert ingest_res["status"] == "SUCCESS"
    
    # Check if a PromptQA node exists with prompt chunk formatting
    cursor = runtime.conn.cursor()
    cursor.execute("SELECT id, path, content, metadata FROM evidence_nodes WHERE id LIKE '%prompt_quality_scores.json#prompt-%'")
    rows = cursor.fetchall()
    
    # We should have ingested several prompt-specific nodes
    assert len(rows) > 0
    
    # Verify metadata contains prompt_id
    meta = json.loads(rows[0]["metadata"])
    assert "prompt_id" in meta

def test_relationship_edge_generation():
    runtime = get_brain_runtime()
    runtime.ingest_artifacts()
    
    cursor = runtime.conn.cursor()
    
    # Verify we created qa_evidence_for relationships
    cursor.execute("SELECT from_node, to_node, relationship_type FROM graph_edges WHERE relationship_type = 'qa_evidence_for'")
    rows = cursor.fetchall()
    assert len(rows) > 0
    assert rows[0]["to_node"].startswith("prompt-")

def test_promptqa_based_gap_closure_validation():
    runtime = get_brain_runtime()
    pm = get_promptbrain_manager()
    qa = get_promptqa_manager()
    
    # Force run pipelines to sync state
    qa.run_eval_pipeline()
    runtime.ingest_artifacts()
    
    # Fetch closures
    res = runtime.validate_gap_closures()
    assert res["status"] == "AUDITED"
    assert "closures" in res
    
    # Check that each gap has a status
    for closure in res["closures"]:
        assert closure["status"] in ["OPEN", "RESOLVED"]
        if closure["status"] == "RESOLVED":
            # Must point to the PromptQA score card JSON as resolver
            assert closure["resolved_by_node"].startswith("artifacts/promptqa/prompt_quality_scores.json#prompt-")

def test_export_zip_compliance_bundle():
    app.config["TESTING"] = True
    with app.test_client() as c:
        r = c.get("/api/v1/brain/export")
        assert r.status_code == 200
        assert r.mimetype == "application/zip"
        
        # Verify it's a valid ZIP and contains expected database/artifacts
        zip_data = io.BytesIO(r.data)
        with zipfile.ZipFile(zip_data, "r") as zf:
            namelist = zf.namelist()
            assert any("brain_evidence.db" in name for name in namelist)
            assert any("artifacts/promptqa/prompt_quality_scores.json" in name for name in namelist)
            assert any("artifacts/promptbrain/revised_master_prompt_library.json" in name for name in namelist)
