# -*- coding: utf-8 -*-
"""
tests/test_promptqa.py — Pytest suite for PROMPTQA1.
"""

import json
from pathlib import Path
import pytest
from flask.testing import FlaskClient

from hoch_agent_swarm.promptbrain_manager import get_promptbrain_manager
from hoch_agent_swarm.promptqa_manager import (
    PromptQaManager,
    get_promptqa_manager,
    QA_TEAM
)
from hoch_agent_swarm.ui_server import app

def test_promptqa_status_loads():
    qa = get_promptqa_manager()
    assert qa.status["promptQaEnabled"] is True
    assert qa.status["totalPromptsEvaluated"] > 100

def test_prompt_quality_scoring_works():
    qa = get_promptqa_manager()
    # Test scoring of specific prompt ID
    p_id = "BRAIN-001"
    assert p_id in qa.scores
    score_info = qa.scores[p_id]
    assert score_info["overall_score"] > 50
    assert "band" in score_info

def test_weakness_detection_identifies_missing_fail_closed():
    qa = get_promptqa_manager()
    # Create dummy prompt missing "fail closed"
    dummy = {
        "id": "TEST-DUMMY",
        "category": "Testing",
        "industry": "All Industries",
        "title": "Dummy test",
        "mission": "Do something",
        "outputs": "none",
        "prompt": "You are a dummy agent. Do something."
    }
    weaknesses = qa._detect_weaknesses(dummy)
    assert "missing fail-closed instruction" in weaknesses

def test_assertion_generation_works():
    qa = get_promptqa_manager()
    p = {
        "id": "GOVFRAME-001",
        "prompt": "Assess security controls."
    }
    assertions = qa._generate_assertions(p)
    assert any("framework control" in a for a in assertions)

def test_regression_cases_are_generated():
    qa = get_promptqa_manager()
    p_id = "BRAIN-001"
    assert p_id in qa.regression_results
    assert qa.regression_results[p_id]["regression_pass"] is True

def test_rewrite_candidates_are_created_without_overwriting_originals():
    qa = get_promptqa_manager()
    pm = get_promptbrain_manager()
    
    # Identify a prompt with candidate rewrite
    low_prompt_id = next(iter(qa.candidates.keys()))
    original_prompt = next(p for p in pm.revised_prompts if p["id"] == low_prompt_id)
    candidate = qa.candidates[low_prompt_id]
    
    assert original_prompt["prompt"] != candidate["rewrittenPrompt"]
    assert candidate["originalId"] == low_prompt_id

def test_rewrite_candidates_default_to_pending_review():
    qa = get_promptqa_manager()
    qa.run_eval_pipeline()
    for p_id, item in qa.approval_queue.items():
        assert item["approvalStatus"] == "pending_review"

def test_approval_gate_refuses_low_scoring_prompts():
    qa = get_promptqa_manager()
    # Inject low scoring candidate
    qa.candidates["TEST-LOW"] = {
        "originalId": "TEST-LOW",
        "candidateId": "TEST-LOW-CANDIDATE",
        "afterScoreEstimate": 50.0,
        "rewrittenPrompt": "Low quality"
    }
    success = qa.approve_candidate("TEST-LOW")
    assert success is False

def test_approval_gate_approves_only_passing_candidates():
    qa = get_promptqa_manager()
    # Inject high scoring candidate
    qa.candidates["TEST-HIGH"] = {
        "originalId": "TEST-HIGH",
        "candidateId": "TEST-HIGH-CANDIDATE",
        "afterScoreEstimate": 95.0,
        "rewrittenPrompt": "High quality fail closed boundary constraints"
    }
    qa.approval_queue["TEST-HIGH"] = {"approvalStatus": "pending_review"}
    qa.lineage["TEST-HIGH"] = [{"version": 1}, {"version": 2}]
    
    # We must ensure TEST-HIGH exists in promptbrain revised prompts
    pm = get_promptbrain_manager()
    pm.revised_prompts.append({
        "id": "TEST-HIGH",
        "category": "Testing",
        "industry": "All Industries",
        "title": "Test High",
        "mission": "High mission",
        "outputs": "high outputs",
        "prompt": "Original prompt text"
    })
    
    success = qa.approve_candidate("TEST-HIGH")
    assert success is True
    
    # Clean up
    pm.revised_prompts = [p for p in pm.revised_prompts if p["id"] != "TEST-HIGH"]

def test_routing_evaluation_returns_expected_prompts_in_top_5():
    qa = get_promptqa_manager()
    pm = get_promptbrain_manager()
    qa._evaluate_routing(pm)
    assert qa.routing_results["routing_eval_score"] > 50
    for detail in qa.routing_results["eval_details"]:
        assert detail["passed"] is True

def test_promptbrain_consumes_promptqa_scores():
    # Flask app should return combined status
    app.config["TESTING"] = True
    with app.test_client() as c:
        r = c.get("/api/v1/promptbrain/status")
        assert r.status_code == 200
        data = r.get_json()
        assert "promptQaEnabled" in data
        assert data["promptQaEnabled"] is True
        assert "averagePromptScore" in data

def test_higher_scored_approved_prompts_rank_above_weaker_prompts():
    pm = get_promptbrain_manager()
    
    # Create two matching prompts
    pm.revised_prompts.append({
        "id": "TEST-ROUTE-A",
        "category": "Testing",
        "industry": "All Industries",
        "title": "Deploy database target",
        "mission": "Deploy database",
        "outputs": "none",
        "prompt": "Prompt A",
        "frameworks": [],
        "recommendedRoutes": []
    })
    pm.revised_prompts.append({
        "id": "TEST-ROUTE-B",
        "category": "Testing",
        "industry": "All Industries",
        "title": "Deploy database target",
        "mission": "Deploy database",
        "outputs": "none",
        "prompt": "Prompt B",
        "frameworks": [],
        "recommendedRoutes": []
    })
    
    # Inject scores to QA manager
    qa = get_promptqa_manager()
    qa.scores["TEST-ROUTE-A"] = {"overall_score": 95.0, "band": "Release Grade"}
    qa.scores["TEST-ROUTE-B"] = {"overall_score": 80.0, "band": "Acceptable"}
    
    res = pm.route_task("Deploy database target")
    recs = res["recommendations"]
    
    # A has higher score, should be ranked first
    ids = [r["id"] for r in recs]
    assert ids.index("TEST-ROUTE-A") < ids.index("TEST-ROUTE-B")
    
    # Clean up
    pm.revised_prompts = [p for p in pm.revised_prompts if p["id"] not in ["TEST-ROUTE-A", "TEST-ROUTE-B"]]

def test_export_bundle_contains_required_promptqa_artifacts():
    app.config["TESTING"] = True
    with app.test_client() as c:
        r = c.get("/api/v1/promptqa/export")
        assert r.status_code == 200
        assert r.mimetype == "application/zip"

def test_ato_package_includes_promptqa_artifacts():
    # Verify files exist in artifacts directory
    from hoch_agent_swarm.promptqa_manager import PROMPTQA_ART_DIR
    assert (PROMPTQA_ART_DIR / "prompt_quality_scores.json").exists()
    assert (PROMPTQA_ART_DIR / "prompt_weakness_register.json").exists()
    assert (PROMPTQA_ART_DIR / "prompt_assertions.json").exists()
    assert (PROMPTQA_ART_DIR / "prompt_regression_results.json").exists()
    assert (PROMPTQA_ART_DIR / "prompt_rewrite_candidates.json").exists()
    assert (PROMPTQA_ART_DIR / "routing_eval_results.json").exists()
    assert (PROMPTQA_ART_DIR / "prompt_approval_queue.json").exists()
    assert (PROMPTQA_ART_DIR / "prompt_lineage.json").exists()

def test_boundary_language_is_present():
    # Notice must be in the scores markdown file
    docs_path = Path(__file__).resolve().parent.parent / "docs" / "PROMPTQA1.md"
    assert docs_path.exists()
    with open(docs_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "PromptQA provides prompt quality, regression, routing, and improvement evidence." in content
        assert "It does not prove full compliance, eliminate risk, or grant ATO." in content

def test_no_actual_ato_claim_is_made():
    docs_path = Path(__file__).resolve().parent.parent / "docs" / "PROMPTQA1.md"
    with open(docs_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "ATO granted" not in content
        assert "Authorized to Operate" not in content
        assert "risk eliminated" not in content
        assert "100% secure" not in content
        assert "100% compliant" not in content
