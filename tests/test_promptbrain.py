# -*- coding: utf-8 -*-
"""
tests/test_promptbrain.py — Pytest suite for PROMPTBRAIN1 features.
"""

import json
from pathlib import Path
import pytest

from hoch_agent_swarm.promptbrain_manager import (
    PromptBrainManager,
    get_promptbrain_manager,
    REQUIRED_FIELDS,
    MISSING_FAMILIES
)

def test_promptbrain_manager_singleton():
    pm1 = get_promptbrain_manager()
    pm2 = get_promptbrain_manager()
    assert pm1 is pm2

def test_promptbrain_ingest_metrics():
    pm = get_promptbrain_manager()
    assert len(pm.prompts) >= 100
    assert pm.import_report["status"] == "PASS"
    assert pm.import_report["total_errors"] == 0

def test_promptbrain_schema_validation():
    pm = get_promptbrain_manager()
    for p in pm.prompts:
        for f in REQUIRED_FIELDS:
            assert f in p
            assert p[f]

def test_gap_analysis_identifies_missing_families():
    pm = get_promptbrain_manager()
    # Gaps should equal the length of MISSING_FAMILIES since none were in the original library
    assert len(pm.gaps) == len(MISSING_FAMILIES)
    assert len(pm.gaps) == 84

    # Verify severity classification
    for gap in pm.gaps:
        p_id = gap["missing_prompt_id"]
        if p_id.startswith("BRAIN-") or p_id.startswith("PROMPT-") or p_id.startswith("GAP-"):
            assert gap["severity"] == "Critical"
        else:
            assert gap["severity"] == "High"

def test_promptbrain_generation_hygiene():
    pm = get_promptbrain_manager()
    assert len(pm.generated_prompts) == 84

    # Verify safety prompt content rules
    for gp in pm.generated_prompts:
        prompt_text = gp["prompt"]
        assert "Facts Observed:" in prompt_text
        assert "Assumptions:" in prompt_text
        assert "Risks:" in prompt_text
        assert "Exact Remediation Actions:" in prompt_text
        assert "Validation Tests:" in prompt_text
        assert "Evidence Artifacts:" in prompt_text
        assert "Release/Audit/Authorization Decision:" in prompt_text
        assert "POA&M Entries:" in prompt_text
        assert "Closure Criteria:" in prompt_text
        assert "Central Brain Ingestion JSON:" in prompt_text
        assert "Fail closed on unresolved high-risk ambiguity." in prompt_text
        assert "Separate facts from assumptions." in prompt_text
        assert "Do not claim authorization, compliance, or risk closure without evidence." in prompt_text

def test_revised_master_prompt_library():
    pm = get_promptbrain_manager()
    # 103 original + 84 generated = 187 total
    assert len(pm.revised_prompts) == 187
    
    # Check that sorting works
    p_ids = [p["id"] for p in pm.revised_prompts]
    assert p_ids == sorted(p_ids)

def test_llm_brain_schema_generation():
    pm = get_promptbrain_manager()
    # Check if files exist
    from hoch_agent_swarm.promptbrain_manager import PROMPTBRAIN_ART_DIR
    
    schema_path = PROMPTBRAIN_ART_DIR / "llm_brain_schema.json"
    seed_path = PROMPTBRAIN_ART_DIR / "knowledge_graph_seed.json"
    policy_path = PROMPTBRAIN_ART_DIR / "retrieval_policy.json"
    
    assert schema_path.exists()
    assert seed_path.exists()
    assert policy_path.exists()

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
        assert "entities" in schema
        assert "relationships" in schema

    with open(policy_path, "r", encoding="utf-8") as f:
        policy = json.load(f)
        assert "ATO-SUPPORTING EVIDENCE PACKAGE: READY FOR REVIEW" in policy["certifications"]

def test_prompt_routing_logic():
    pm = get_promptbrain_manager()
    
    # Normal query
    res = pm.route_task("Audit federal civilian database and test vulnerability settings", framework="NIST SP 800-53 Rev. 5")
    assert res["status"] == "SUCCESS"
    assert res["risk_level"] == "LOW"
    assert len(res["recommendations"]) > 0
    # First recommendation should probably be a GOVFRAME or related prompt
    assert any("GOVFRAME-" in rec["id"] for rec in res["recommendations"])

    # High risk action requiring human review
    res_high = pm.route_task("Deploy firewall rules and delete logs")
    assert res_high["risk_level"] == "HIGH"
    assert res_high["human_approval_required"] is True

    # Bypass approval attempt -> FAIL_CLOSED
    res_bypass = pm.route_task("Deploy code immediately and skip approval workflow")
    assert res_bypass["status"] == "FAIL_CLOSED"
    assert res_bypass["risk_level"] == "FAIL_CLOSED"
    assert "BYPASS_APPROVAL_ATTEMPTED" in res_bypass["fail_closed_triggers"]
    assert "TASK_EXECUTION_BLOCKED" in res_bypass["blocked_actions"]

def test_flask_api_routing(client=None):
    # Test through Flask test client if app is initialized
    from hoch_agent_swarm.ui_server import app
    app.config["TESTING"] = True
    with app.test_client() as c:
        # Status
        r = c.get("/api/v1/promptbrain/status")
        assert r.status_code == 200
        data = r.get_json()
        assert data["total_revised"] == 187
        assert data["total_gaps"] == 84

        # Gaps
        r = c.get("/api/v1/promptbrain/gaps")
        assert r.status_code == 200
        assert len(r.get_json()) == 84

        # Schema
        r = c.get("/api/v1/promptbrain/brain-schema")
        assert r.status_code == 200

        # Routing simulation
        r = c.post("/api/v1/promptbrain/route", json={
            "task_description": "Assess CMMC 2.0 readiness gaps",
            "framework": "CMMC 2.0"
        })
        assert r.status_code == 200
        data = r.get_json()
        assert data["status"] == "SUCCESS"
        assert len(data["recommendations"]) > 0

        # Export zip
        r = c.get("/api/v1/promptbrain/export")
        assert r.status_code == 200
        assert r.mimetype == "application/zip"
