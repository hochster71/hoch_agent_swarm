import os
import json
from pathlib import Path
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "prompt_brain"

def test_prompt_selection():
    from scripts.prompt_brain.prompt_runtime_orchestrator import PromptRuntimeOrchestrator
    orchestrator = PromptRuntimeOrchestrator()
    
    prompt = orchestrator.select_prompt(
        domain="Cybersecurity",
        role="Cybersecurity Engineer",
        task="Establish zero-trust network boundaries and micro-segmentation guidelines.",
        family="SOP Prompt"
    )
    assert prompt is not None
    assert "prompt_id" in prompt
    assert prompt["prompt_family"] == "SOP Prompt"
    assert "Security Analyst" in prompt["occupation"] or "Information Security" in prompt["occupation"]

def test_execution_and_critique_success():
    from scripts.prompt_brain.prompt_runtime_orchestrator import PromptRuntimeOrchestrator
    orchestrator = PromptRuntimeOrchestrator()
    
    res = orchestrator.execute_mission(
        domain="Cybersecurity",
        role="Cybersecurity Engineer",
        task="Establish zero-trust network boundaries.",
        family="SOP Prompt",
        inputs={"network": "dmz-1"}
    )
    assert res["passed"] is True
    assert res["qa_score"] >= 90
    assert res["critic_score"] >= 85
    assert res["repair_status"] in ["NONE", "REPAIRED"]

def test_execution_and_critique_failure_repair():
    from scripts.prompt_brain.prompt_runtime_orchestrator import PromptRuntimeOrchestrator
    orchestrator = PromptRuntimeOrchestrator()
    
    res = orchestrator.execute_mission(
        domain="Cybersecurity",
        role="Cybersecurity Engineer",
        task="Establish zero-trust network boundaries.",
        family="SOP Prompt",
        inputs={"network": "dmz-1"},
        force_fail=True
    )
    assert res["repair_status"] == "REPAIRED"
    assert res["passed"] is True
    assert res["qa_score"] >= 90
    
    queue_path = DATA_DIR / "prompt_repair_queue.jsonl"
    assert queue_path.exists()
    found = False
    with open(queue_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                t = json.loads(line)
                if t["execution_id"] == res["execution_id"]:
                    found = True
                    break
    assert found

def test_runtime_endpoints():
    response = client.get("/api/prompt-brain/runtime/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ONLINE"
    assert "total_executions" in data

    response = client.get("/api/prompt-brain/runtime/executions")
    assert response.status_code == 200
    data = response.json()
    assert "executions" in data
    assert isinstance(data["executions"], list)

    response = client.get("/api/prompt-brain/model-performance")
    assert response.status_code == 200
    data = response.json()
    assert "Tier 1 (High Reasoning)" in data

    response = client.post("/api/prompt-brain/runtime/execute", json={
        "domain": "Cybersecurity",
        "role": "Cybersecurity Engineer",
        "task": "Audit cryptographic key lifecycles.",
        "family": "SOP Prompt"
    })
    assert response.status_code == 200
    res = response.json()
    assert res["passed"] is True

    response = client.post("/api/prompt-brain/runtime/repair", json={
        "prompt_id": res["prompt_id"],
        "remediation_fixes": "Ensure fail-closed fallback headers."
    })
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_baseline_vs_prompt_brain_win_rate():
    eval_path = DATA_DIR / "baseline_vs_prompt_brain_eval.jsonl"
    assert eval_path.exists()
    
    wins = 0
    total = 0
    with open(eval_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                ev = json.loads(line)
                total += 1
                if ev["winner"] == "Prompt Brain":
                    wins += 1
    
    assert total == 8
    assert wins >= 6  # Prompt Brain must win in at least 6 out of 8 domains

def test_red_team_severity_gate():
    rt_path = DATA_DIR / "red_team_gate_audit.json"
    assert rt_path.exists()
    with open(rt_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    assert "by_severity" in data
    assert "rejections" in data
    assert data["total_rejected"] > 0
    for r in data["rejections"]:
        assert r["severity"] in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFORMATIONAL"]
        assert r["vulnerability"] != ""

def test_taxonomy_expansion_coverage():
    tax_path = DATA_DIR / "taxonomy_expansion_status.json"
    assert tax_path.exists()
    with open(tax_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    for key in ["total_naics_sectors_available", "total_naics_sectors_ingested", "coverage_percentage", "missing_sectors"]:
        assert key in data
    assert data["coverage_percentage"] > 0.0

def test_monetizable_prompt_packs():
    packs_dir = DATA_DIR / "packs"
    assert packs_dir.exists()
    
    packs_files = [
        "cybersecurity_prompt_pack.json",
        "devsecops_prompt_pack.json",
        "rmf_ato_conmon_prompt_pack.json",
        "qa_red_team_prompt_pack.json",
        "software_factory_prompt_pack.json"
    ]
    
    for pf in packs_files:
        p_path = packs_dir / pf
        assert p_path.exists()
        with open(p_path, "r", encoding="utf-8") as f:
            pack = json.load(f)
        
        required_fields = [
            "pack_name",
            "target_buyer",
            "pricing_hypothesis",
            "use_cases",
            "included_prompt_families",
            "approved_prompts",
            "qa_score_summary",
            "red_team_summary",
            "sample_workflows",
            "deployment_instructions",
            "risks_and_disclaimers"
        ]
        for field in required_fields:
            assert field in pack

def test_phase_3_api_endpoints():
    endpoints = [
        "/api/prompt-brain/effectiveness",
        "/api/prompt-brain/red-team-gate",
        "/api/prompt-brain/taxonomy-expansion",
        "/api/prompt-brain/packs"
    ]
    for ep in endpoints:
        response = client.get(ep)
        assert response.status_code == 200
        assert isinstance(response.json(), dict)
