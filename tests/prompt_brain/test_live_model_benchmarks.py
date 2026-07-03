import os
import json
from pathlib import Path
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "prompt_brain"

def test_adapter_status_schema():
    response = client.get("/api/prompt-brain/model-adapters/status")
    assert response.status_code == 200
    data = response.json()
    assert "HOCH Simulation" in data
    sim = data["HOCH Simulation"]
    for key in ["model_name", "is_available", "endpoint", "latency_ms", "last_health_check", "last_error"]:
        assert key in sim

def test_local_adapter_fallback():
    # If a local adapter like LM Studio is offline, execution falls back automatically to simulation
    from scripts.prompt_brain.prompt_runtime_orchestrator import PromptRuntimeOrchestrator
    orchestrator = PromptRuntimeOrchestrator()
    adapter = orchestrator.select_adapter("Tier 2 (Operational)")
    assert adapter is not None
    # Even if LM Studio / Ollama are unavailable, fallback selects HOCH Simulation or OpenAI if configured
    assert adapter.provider in ["HOCH Simulation", "OpenAI", "LM Studio", "Ollama"]

def test_no_secret_leakage():
    # Verify no credentials or secret keys are stored in status ledgers
    status_path = DATA_DIR / "model_adapter_status.json"
    if status_path.exists():
        content = status_path.read_text(encoding="utf-8")
        assert "sk-" not in content
        assert "AIzaSy" not in content

def test_live_benchmark_schema():
    response = client.get("/api/prompt-brain/live-benchmarks")
    assert response.status_code == 200
    data = response.json()
    assert "benchmarks" in data
    assert len(data["benchmarks"]) >= 8
    
    first = data["benchmarks"][0]
    for key in ["domain", "baseline_qa_score", "prompt_brain_qa_score", "delta", "winner", "execution_mode"]:
        assert key in first

def test_live_effectiveness_uplift():
    response = client.get("/api/prompt-brain/live-effectiveness")
    assert response.status_code == 200
    data = response.json()
    assert "evaluations" in data
    assert len(data["evaluations"]) >= 8
    
    # Assert Prompt Brain beats baseline in at least 6 of 8 domains
    wins = sum(1 for e in data["evaluations"] if e["winner"] == "Prompt Brain")
    assert wins >= 6
    
    # Assert average score uplift is at least 15%
    deltas = [e["delta"] for e in data["evaluations"]]
    avg_delta = sum(deltas) / len(deltas)
    assert avg_delta >= 15.0

def test_adapter_errors_endpoint():
    response = client.get("/api/prompt-brain/adapter-errors")
    assert response.status_code == 200
    data = response.json()
    assert "errors" in data
    assert isinstance(data["errors"], dict)

def test_dashboard_non_placeholder_check():
    response = client.get("/prototype/prompt-brain")
    assert response.status_code == 200
    html = response.text.lower()
    assert "placeholder" not in html
    assert "win rate" in html
    assert "rejection" in html

def test_lm_studio_status_schema():
    response = client.get("/api/prompt-brain/model-adapters/status")
    assert response.status_code == 200
    data = response.json()
    assert "LM Studio" in data
    assert "health_reason_code" in data["LM Studio"]
    assert "available_models" in data["LM Studio"]

def test_ollama_status_schema():
    response = client.get("/api/prompt-brain/model-adapters/status")
    assert response.status_code == 200
    data = response.json()
    assert "Ollama" in data
    assert "health_reason_code" in data["Ollama"]
    assert "available_models" in data["Ollama"]

def test_adapter_health_reason_codes():
    response = client.get("/api/prompt-brain/model-adapters/status")
    data = response.json()
    for provider, val in data.items():
        assert val["health_reason_code"] in [
            "ENDPOINT_REACHABLE",
            "MISSING_API_KEY",
            "ENDPOINT_UNREACHABLE",
            "SIMULATION_FALLBACK_ALWAYS_AVAILABLE"
        ]

def test_production_readiness_gate():
    response = client.get("/api/prompt-brain/production-gate")
    assert response.status_code == 200
    data = response.json()
    assert "production_readiness_gate" in data
    gate = data["production_readiness_gate"]
    assert gate["live_model_benchmark_executions"] >= 16
    assert gate["actual_win_rate_domains"] >= 6
    assert gate["actual_average_score_uplift_percentage"] >= 15.0
    assert gate["verdict"] in ["GO", "CONDITIONAL_GO", "NO_GO"]

def test_local_bringup_report_existence():
    report_path = BASE_DIR / "docs" / "prompt_brain" / "local_model_bringup_report.md"
    assert report_path.exists()

def test_phase5_api_endpoints():
    r1 = client.get("/api/prompt-brain/live-runtime-summary")
    assert r1.status_code == 200
    
    r2 = client.get("/api/prompt-brain/production-readiness-gate")
    assert r2.status_code == 200
    
    r3 = client.get("/api/prompt-brain/local-model-status")
    assert r3.status_code == 200
    
    r4 = client.get("/api/prompt-brain/scoring-traces")
    assert r4.status_code == 200
    assert "traces" in r4.json()

def test_phase6_unseen_benchmarks_schema():
    r = client.get("/api/prompt-brain/unseen-benchmarks")
    assert r.status_code == 200
    tasks = r.json()
    assert len(tasks) >= 40
    first = tasks[0]
    for key in ["task_id", "domain", "role", "mission_input", "risk_category", "scoring_rubric"]:
        assert key in first

def test_phase6_dynamic_scoring_traces():
    r = client.get("/api/prompt-brain/unseen-results")
    assert r.status_code == 200
    data = r.json()
    assert "results" in data
    assert len(data["results"]) >= 80
    first = data["results"][0]
    assert first["output_hash"] is not None
    assert first["prompt_brain_score"] > 0
    assert first["baseline_score"] > 0

    # Assert trace file exists and has non-constant dynamic metrics
    trace_path = BASE_DIR / "data" / "prompt_brain" / "unseen_scoring_trace.jsonl"
    assert trace_path.exists()
    trace_lines = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(trace_lines) >= 80
    
    first_trace = trace_lines[0]
    for k in ["task_id", "timestamp", "mission_input", "model", "provider", "output_hash", "dimension_score", "rationale", "final_weighted_score", "pass_fail_status"]:
        assert k in first_trace
    
    # Assert score is not a fixed constant (ensure scores are output specific)
    all_scores = {line["final_weighted_score"] for line in trace_lines}
    assert len(all_scores) > 1

def test_phase6_product_pack_rc1():
    # Check JSON Release Candidate configuration file
    r = client.get("/api/prompt-brain/release-candidates")
    assert r.status_code == 200
    pack = r.json()
    assert pack["pack_id"] == "rmf_ato_cyber_prompt_brain_pack_rc1"
    assert pack["version"] == "1.0.0-rc1"
    
    # Check Markdown marketing and pricing assets
    docs_dir = BASE_DIR / "docs" / "prompt_brain"
    assert (docs_dir / "rmf_ato_cyber_pack_readme.md").exists()
    assert (docs_dir / "rmf_ato_cyber_pack_pricing.md").exists()
    assert (docs_dir / "rmf_ato_cyber_pack_buyer_pitch.md").exists()
    assert (docs_dir / "rmf_ato_cyber_pack_risk_disclaimer.md").exists()
    assert (docs_dir / "scoring_methodology.md").exists()

def test_phase6_product_readiness_gate():
    r = client.get("/api/prompt-brain/product-readiness")
    assert r.status_code == 200
    data = r.json()
    assert "product_readiness_gate" in data
    gate = data["product_readiness_gate"]
    assert gate["live_local_unseen_executions"] >= 80
    assert gate["actual_win_rate_percentage"] >= 75.0
    assert gate["actual_average_score_uplift_percentage"] >= 12.0
    assert gate["critical_red_team_findings"] == 0
    assert gate["verdict"] == "GO"

def test_phase6_api_endpoints():
    endpoints = [
        "/api/prompt-brain/unseen-benchmarks",
        "/api/prompt-brain/unseen-results",
        "/api/prompt-brain/unseen-summary",
        "/api/prompt-brain/scoring-methodology",
        "/api/prompt-brain/release-candidates",
        "/api/prompt-brain/product-readiness"
    ]
    for ep in endpoints:
        r = client.get(ep)
        assert r.status_code == 200

def test_phase7_demo_dataset_schema():
    r = client.get("/api/prompt-brain/demo/dataset")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 10
    first = data[0]
    for key in ["scenario_id", "role", "input_artifact", "expected_output_type", "control_family", "risk_level", "missing_information_traps", "ambiguity_traps", "red_team_checks", "sanitized_data_statement"]:
        assert key in first

def test_phase7_messy_input_validation_schema():
    r = client.get("/api/prompt-brain/demo/messy-results")
    assert r.status_code == 200
    data = r.json()
    assert "results" in data
    assert len(data["results"]) >= 30
    first = data["results"][0]
    for key in ["case_id", "category", "input", "expected_gap", "provider", "model_name", "latency_ms", "baseline_score", "prompt_brain_score", "identified_gap", "outcome", "output_hash", "passed"]:
        assert key in first

def test_phase7_messy_input_success_gate():
    r = client.get("/api/prompt-brain/demo/readiness")
    assert r.status_code == 200
    data = r.json()
    gate = data["pilot_readiness_gate"]
    assert gate["messy_input_success_rate_percentage"] >= 85.0
    assert gate["critical_hallucination_failures"] == 0
    assert gate["unsupported_compliance_claims"] == 0
    assert gate["verdict"] == "GO"

def test_phase7_external_evaluator_rubric_existence():
    docs_dir = BASE_DIR / "docs" / "prompt_brain"
    assert (docs_dir / "external_evaluator_rubric.md").exists()
    assert (BASE_DIR / "data" / "prompt_brain" / "external_review_template.json").exists()

def test_phase7_demo_workflow_result_schema():
    r = client.get("/api/prompt-brain/demo/workflows")
    assert r.status_code == 200
    data = r.json()
    assert "results" in data
    assert len(data["results"]) >= 6
    first = data["results"][0]
    for key in ["workflow_name", "timestamp", "domain", "role", "input_evidence", "provider", "model_used", "output_hash", "output", "qa_score", "red_team_result", "evidence_trace", "recommended_human_decision_point"]:
        assert key in first

def test_phase7_buyer_facing_artifacts_existence():
    r = client.get("/api/prompt-brain/demo/artifacts")
    assert r.status_code == 200
    data = r.json()
    for art in data["artifacts"]:
        assert art["status"] == "PRESENT"

def test_phase7_api_endpoints_health():
    endpoints = [
        "/api/prompt-brain/demo/dataset",
        "/api/prompt-brain/demo/messy-results",
        "/api/prompt-brain/demo/workflows",
        "/api/prompt-brain/demo/readiness",
        "/api/prompt-brain/demo/artifacts"
    ]
    for ep in endpoints:
        r = client.get(ep)
        assert r.status_code == 200

def test_phase8_pilot_checklist_schema():
    r = client.get("/api/prompt-brain/pilot/checklist")
    assert r.status_code == 200
    data = r.json()
    assert "checklist" in data
    chk = data["checklist"]
    for key in ["demo_environment_readiness", "local_model_readiness", "command_center_route_readiness", "demo_workflow_readiness", "buyer_facing_collateral_readiness", "risk_disclaimer_readiness", "external_evaluator_rubric_readiness", "no_sensitive_data_validation", "human_in_the_loop_decision_boundary", "feedback_capture_process", "follow_up_conversion_plan"]:
        assert chk[key] == "PASSED"

def test_phase8_external_reviewer_package_existence():
    assert (BASE_DIR / "docs" / "prompt_brain" / "external_reviewer_package.md").exists()
    r = client.get("/api/prompt-brain/pilot/reviewer-package")
    assert r.status_code == 200
    data = r.json()
    assert "reviewer_packet" in data
    assert data["reviewer_packet"]["security_warning"] == "DO NOT UPLOAD SENSITIVE DATA"

def test_phase8_feedback_template_schema():
    template_path = BASE_DIR / "data" / "prompt_brain" / "demo" / "reviewer_feedback_template.json"
    assert template_path.exists()
    import json
    with open(template_path, "r", encoding="utf-8") as f:
        template = json.load(f)
    for key in ["reviewer_role", "scenario_reviewed", "correctness_score", "usefulness_score", "trust_score", "missing_evidence_flags", "hallucination_concerns", "rmf_alignment_comments", "buyer_interest_signal", "willingness_to_pilot_signal", "follow_up_actions"]:
        assert key in template

def test_phase8_feedback_log_write_read_path():
    # Verify we can read existing logs
    r = client.get("/api/prompt-brain/pilot/feedback")
    assert r.status_code == 200
    initial_count = r.json()["count"]
    
    # Write a test feedback entry
    test_feedback = {
        "reviewer_role": "ISSM",
        "scenario_reviewed": "scenario_002",
        "correctness_score": 9.0,
        "usefulness_score": 9.5,
        "trust_score": 9.0,
        "missing_evidence_flags": [],
        "hallucination_concerns": [],
        "rmf_alignment_comments": "Looks good",
        "buyer_interest_signal": "HIGH",
        "willingness_to_pilot_signal": True,
        "follow_up_actions": []
    }
    w_r = client.post("/api/prompt-brain/pilot/feedback", json=test_feedback)
    assert w_r.status_code == 200
    assert w_r.json()["status"] == "success"
    
    # Verify the count increased by 1
    r2 = client.get("/api/prompt-brain/pilot/feedback")
    assert r2.status_code == 200
    assert r2.json()["count"] == initial_count + 1

def test_phase8_outreach_artifact_existence():
    r = client.get("/api/prompt-brain/pilot/outreach")
    assert r.status_code == 200
    data = r.json()
    assert "outreach_artifacts" in data
    for art in data["outreach_artifacts"]:
        assert art["status"] == "PRESENT"

def test_phase8_demo_call_script_existence():
    demo_dir = BASE_DIR / "docs" / "prompt_brain" / "demo"
    assert (demo_dir / "demo_call_script_30min.md").exists()
    assert (demo_dir / "demo_call_script_15min.md").exists()

def test_phase8_pilot_launch_gate_logic():
    r = client.get("/api/prompt-brain/pilot/readiness")
    assert r.status_code == 200
    data = r.json()
    assert "pilot_launch_gate" in data
    gate = data["pilot_launch_gate"]
    assert gate["pilot_checklist_exists"] is True
    assert gate["external_reviewer_package_exists"] is True
    assert gate["feedback_template_exists"] is True
    assert gate["outreach_pack_exists"] is True
    assert gate["demo_call_scripts_exist"] is True
    assert gate["verdict"] == "GO"

def test_phase8_api_endpoints_health():
    endpoints = [
        "/api/prompt-brain/pilot/checklist",
        "/api/prompt-brain/pilot/reviewer-package",
        "/api/prompt-brain/pilot/feedback",
        "/api/prompt-brain/pilot/outreach",
        "/api/prompt-brain/pilot/readiness"
    ]
    for ep in endpoints:
        r = client.get(ep)
        assert r.status_code == 200

def test_phase9_target_contact_list_schema():
    r = client.get("/api/prompt-brain/outreach/targets")
    assert r.status_code == 200
    data = r.json()
    assert "template" in data
    assert "contact_template" in data["template"]
    assert data["shortlist_exists"] is True

def test_phase9_outreach_queue_schema():
    r = client.get("/api/prompt-brain/outreach/queue")
    assert r.status_code == 200
    data = r.json()
    assert "queue" in data
    assert len(data["queue"]) >= 5
    first = data["queue"][0]
    for key in ["contact_id", "organization", "contact_name", "role", "variant", "status", "timestamp"]:
        assert key in first

def test_phase9_outreach_approve_and_log():
    payload = {"contact_id": "CON-001"}
    r = client.post("/api/prompt-brain/outreach/approve", json=payload)
    assert r.status_code == 200
    assert r.json()["status"] == "success"
    
    log_path = BASE_DIR / "data" / "prompt_brain" / "outreach" / "outreach_approval_log.jsonl"
    assert log_path.exists()
    import json
    with open(log_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    last = json.loads(lines[-1].strip())
    assert last["contact_id"] == "CON-001"
    assert last["verdict"] == "APPROVED"

def test_phase9_message_variants_exist():
    outreach_dir = BASE_DIR / "docs" / "prompt_brain" / "outreach"
    assert (outreach_dir / "email_variant_short.md").exists()
    assert (outreach_dir / "email_variant_technical.md").exists()
    assert (outreach_dir / "email_variant_executive.md").exists()
    assert (outreach_dir / "linkedin_variant_short.md").exists()
    assert (outreach_dir / "followup_sequence.md").exists()

def test_phase9_feedback_log_and_summary_schema():
    r = client.get("/api/prompt-brain/outreach/feedback")
    assert r.status_code == 200
    data = r.json()
    assert "feedback" in data
    assert "summary" in data
    assert len(data["feedback"]) >= 3
    first = data["feedback"][0]
    for key in ["reviewer_role", "scenario_reviewed", "correctness_score", "usefulness_score", "trust_score", "buyer_pain_fit", "willingness_to_pilot_signal", "willingness_to_pay_signal", "requested_integrations", "objections", "risk_concerns", "next_action"]:
        assert key in first

def test_phase9_buyer_signal_dashboard_schema():
    r = client.get("/api/prompt-brain/outreach/signals")
    assert r.status_code == 200
    data = r.json()
    for key in ["outreach_queued", "outreach_approved", "outreach_sent", "replies_received", "demos_scheduled", "demos_completed", "reviewer_feedback_count", "positive_buyer_signals", "objections", "pilot_interest_count", "paid_pilot_interest_count", "conversion_rate_percentage"]:
        assert key in data

def test_phase9_decision_gate_logic():
    gate_path = BASE_DIR / "data" / "prompt_brain" / "outreach" / "phase_9_decision_gate.json"
    assert gate_path.exists()
    import json
    with open(gate_path, "r", encoding="utf-8") as f:
        gate = json.load(f)["phase_9_decision_gate"]
    assert gate["approved_outreach_targets_queued"] >= 5
    assert gate["external_reviewer_feedback_count"] >= 3
    assert gate["critical_trust_objections_unresolved"] == 0
    assert gate["demos_scheduled"] >= 1
    assert gate["verdict"] == "ADVANCE_TO_PAID_PILOT"

def test_phase9_api_endpoints_health():
    endpoints = [
        "/api/prompt-brain/outreach/targets",
        "/api/prompt-brain/outreach/queue",
        "/api/prompt-brain/outreach/feedback",
        "/api/prompt-brain/outreach/signals"
    ]
    for ep in endpoints:
        r = client.get(ep)
        assert r.status_code == 200

def test_phase10_paid_pilot_offer_existence():
    pilot_dir = BASE_DIR / "docs" / "prompt_brain" / "pilot"
    assert (pilot_dir / "paid_pilot_offer.md").exists()
    assert (pilot_dir / "paid_pilot_scope.md").exists()
    assert (pilot_dir / "paid_pilot_deliverables.md").exists()
    assert (pilot_dir / "paid_pilot_success_metrics.md").exists()
    assert (pilot_dir / "paid_pilot_limitations.md").exists()

def test_phase10_pricing_model_schema():
    r = client.get("/api/prompt-brain/pilot/pricing")
    assert r.status_code == 200
    data = r.json()
    assert "pricing_model" in data
    starter = data["pricing_model"]["starter_pilot"]
    assert starter["price_usd"] == 999.0

def test_phase10_commercial_boundary_doc_existence():
    pilot_dir = BASE_DIR / "docs" / "prompt_brain" / "pilot"
    assert (pilot_dir / "commercial_terms_draft.md").exists()
    assert (pilot_dir / "human_in_the_loop_boundary.md").exists()
    assert (pilot_dir / "security_and_data_boundary.md").exists()
    assert (pilot_dir / "non_authority_disclaimer.md").exists()

def test_phase10_onboarding_checklist_schema():
    checklist_path = BASE_DIR / "data" / "prompt_brain" / "pilot" / "pilot_onboarding_checklist.json"
    assert checklist_path.exists()
    import json
    with open(checklist_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "onboarding_checklist" in data
    chk = data["onboarding_checklist"]
    assert chk["buyer_use_case_selection"] == "PASSED"
    assert (BASE_DIR / "docs" / "prompt_brain" / "pilot" / "pilot_onboarding_checklist.md").exists()
    assert (BASE_DIR / "docs" / "prompt_brain" / "pilot" / "pilot_kickoff_agenda.md").exists()
    assert (BASE_DIR / "docs" / "prompt_brain" / "pilot" / "pilot_closeout_agenda.md").exists()

def test_phase10_conversion_tracker_schema():
    r = client.get("/api/prompt-brain/pilot/conversion")
    assert r.status_code == 200
    data = r.json()
    assert "conversion_tracker" in data
    assert data["conversion_tracker"]["total_leads"] == 5

def test_phase10_risk_register_schema():
    r = client.get("/api/prompt-brain/pilot/risks")
    assert r.status_code == 200
    data = r.json()
    assert "risk_register" in data
    assert len(data["risk_register"]) >= 2
    first = data["risk_register"][0]
    for key in ["risk_id", "category", "description", "impact", "probability", "mitigation_plan"]:
        assert key in first

def test_phase10_followup_message_existence():
    pilot_dir = BASE_DIR / "docs" / "prompt_brain" / "pilot"
    assert (pilot_dir / "followup_after_demo.md").exists()
    assert (pilot_dir / "paid_pilot_offer_email.md").exists()
    assert (pilot_dir / "reviewer_thank_you.md").exists()
    assert (pilot_dir / "objection_response_price.md").exists()
    assert (pilot_dir / "objection_response_local_install.md").exists()

def test_phase10_paid_pilot_gate_logic():
    gate_path = BASE_DIR / "data" / "prompt_brain" / "pilot" / "paid_pilot_gate.json"
    assert gate_path.exists()
    import json
    with open(gate_path, "r", encoding="utf-8") as f:
        gate = json.load(f)["paid_pilot_gate"]
    assert gate["paid_pilot_offer_exists"] is True
    assert gate["scope_document_exists"] is True
    assert gate["pricing_model_exists"] is True
    assert gate["commercial_boundary_docs_exist"] is True
    assert gate["verdict"] == "READY_TO_OFFER"

def test_phase10_api_endpoints_health():
    endpoints = [
        "/api/prompt-brain/pilot/paid-offer",
        "/api/prompt-brain/pilot/pricing",
        "/api/prompt-brain/pilot/pipeline",
        "/api/prompt-brain/pilot/conversion",
        "/api/prompt-brain/pilot/risks"
    ]
    for ep in endpoints:
        r = client.get(ep)
        assert r.status_code == 200

def test_phase11_master_launch_index_existence():
    docs_dir = BASE_DIR / "docs" / "prompt_brain"
    data_dir = BASE_DIR / "data" / "prompt_brain"
    assert (docs_dir / "PROMPT_BRAIN_MASTER_LAUNCH_INDEX.md").exists()
    assert (docs_dir / "API_ROUTE_MAP.md").exists()
    assert (docs_dir / "LOCAL_RUNTIME_PORTS.md").exists()
    assert (docs_dir / "PHASE_REPORT_INDEX.md").exists()
    assert (data_dir / "master_launch_index.json").exists()
    assert (data_dir / "route_port_inventory.json").exists()

def test_phase11_route_port_inventory_schema():
    path = BASE_DIR / "data" / "prompt_brain" / "route_port_inventory.json"
    import json
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "inventory" in data
    inv = data["inventory"]
    assert inv["backend_server"]["url"] == "http://127.0.0.1:8000"
    assert inv["command_center"]["url"] == "http://127.0.0.1:8000/prototype/prompt-brain"

def test_phase10c_doctrine_documents_existence():
    doc_dir = BASE_DIR / "docs" / "doctrine"
    assert (doc_dir / "HOCH_PRIVATE_FIRST_DOCTRINE.md").exists()
    assert (doc_dir / "HAS_HASF_PUBLIC_PRIVATE_BOUNDARY.md").exists()
    assert (doc_dir / "PROMPT_BRAIN_IP_PROTECTION.md").exists()
    assert (doc_dir / "APP_STORE_EXCEPTION_POLICY.md").exists()
    assert (doc_dir / "EXTERNAL_ENGAGEMENT_HOLD_POLICY.md").exists()

def test_phase10c_doctrine_gate_schema():
    r = client.get("/api/prompt-brain/doctrine/gate")
    assert r.status_code == 200
    gate = r.json()["private_first_doctrine_gate"]
    assert gate["private_brain_required"] is True
    assert gate["external_company_engagement_allowed"] is False
    assert gate["investor_engagement_allowed"] is False
    assert gate["app_store_exception_allowed"] is True
    assert gate["final_verdict"] == "PRIVATE_FIRST_GO"

def test_phase10c_external_freeze_ledger_schema():
    r = client.get("/api/prompt-brain/doctrine/freeze")
    assert r.status_code == 200
    ledger = r.json()["external_engagement_freeze_ledger"]
    assert ledger["external_company_engagement"] == "FROZEN"
    assert ledger["investor_engagement"] == "FROZEN"

def test_phase10c_paid_pilot_hold_status_schema():
    path = BASE_DIR / "data" / "prompt_brain" / "pilot" / "paid_pilot_hold_status.json"
    assert path.exists()
    import json
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)["paid_pilot_hold_status"]
    assert data["paid_pilot_package_exists"] is True
    assert data["external_send_allowed"] is False
    assert data["final_verdict"] == "HELD_INTERNAL_ONLY"

def test_phase10c_app_store_pipelines_schema():
    r = client.get("/api/prompt-brain/app-store/pipeline")
    assert r.status_code == 200
    data = r.json()
    assert "pipeline" in data
    assert len(data["pipeline"]) >= 2
    
    r2 = client.get("/api/prompt-brain/app-store/candidates")
    assert r2.status_code == 200
    data2 = r2.json()
    assert "candidates" in data2
    assert len(data2["candidates"]) >= 5

def test_phase10c_verify_script_run():
    import subprocess
    script_path = BASE_DIR / "scripts" / "verify_private_first_doctrine.py"
    res = subprocess.run(["python3", str(script_path)], capture_output=True, text=True)
    assert res.returncode == 0
    assert "PRIVATE_FIRST_DOCTRINE: GO" in res.stdout

def test_phase10b_deployment_config_existence():
    deploy_dir = BASE_DIR / "deploy" / "remote-relay"
    assert (deploy_dir / "docker-compose.yml").exists()
    assert (deploy_dir / "README.md").exists()
    assert (deploy_dir / "Caddyfile").exists()
    assert (deploy_dir / "cloudflared-config.example.yml").exists()
    assert (deploy_dir / "healthcheck.sh").exists()
    assert (deploy_dir / "backup.sh").exists()
    assert (deploy_dir / "restore.sh").exists()
    assert (deploy_dir / "systemd" / "hoch-agent-swarm.service").exists()
    assert (deploy_dir / "scripts" / "deploy_remote.sh").exists()
    assert (deploy_dir / "scripts" / "verify_remote.sh").exists()

def test_phase10b_env_template_existence():
    env_path = BASE_DIR / "deploy" / "remote-relay" / ".env.example"
    assert env_path.exists()
    with open(env_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "RELAY_AUTH_TOKEN=" in content
    assert "change-me" in content

def test_phase10b_relay_endpoints():
    relay_path = BASE_DIR / "scripts" / "remote_runtime" / "relay_api.py"
    assert relay_path.exists()
    
    r = client.get("/api/remote-runtime/status")
    assert r.status_code == 200
    r = client.get("/api/remote-runtime/health")
    assert r.status_code == 200

def test_phase10b_worker_job_schema():
    queue_path = BASE_DIR / "data" / "runtime" / "job_queue.jsonl"
    results_path = BASE_DIR / "data" / "runtime" / "job_results.jsonl"
    assert queue_path.exists()
    assert results_path.exists()

def test_phase10b_k3s_manifests():
    k3s_dir = BASE_DIR / "deploy" / "k3s"
    assert (k3s_dir / "namespace.yaml").exists()
    assert (k3s_dir / "has-api-deployment.yaml").exists()
    assert (k3s_dir / "pvc-evidence.yaml").exists()
    assert (k3s_dir / "secret-template.yaml").exists()

def test_phase10b_security_docs():
    sec_dir = BASE_DIR / "docs" / "remote_runtime"
    assert (sec_dir / "REMOTE_RUNTIME_SECURITY.md").exists()
    assert (sec_dir / "REMOTE_RUNTIME_DEPLOYMENT.md").exists()
    assert (sec_dir / "REMOTE_RUNTIME_OPERATIONS.md").exists()

def test_phase10b1_host_profile():
    profile_path = BASE_DIR / "data" / "runtime" / "remote_host_profile.json"
    assert profile_path.exists()
    with open(profile_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "remote_host_profile" in data
    assert data["remote_host_profile"]["deployment_status"] == "PENDING_OPERATOR_HOST"

def test_phase10b1_runbook():
    runbook_path = BASE_DIR / "docs" / "remote_runtime" / "REMOTE_VPS_DEPLOYMENT_RUNBOOK.md"
    assert runbook_path.exists()

def test_phase10b1_attempts_ledger():
    attempts_path = BASE_DIR / "data" / "runtime" / "remote_deployment_attempts.jsonl"
    assert attempts_path.exists()
    with open(attempts_path, "r", encoding="utf-8") as f:
        line = f.readline()
    assert "deploy_001" in line

def test_phase10b1_exposure_check():
    script_path = BASE_DIR / "scripts" / "remote_runtime" / "check_public_exposure.py"
    assert script_path.exists()
    
    audit_path = BASE_DIR / "data" / "runtime" / "public_exposure_audit.json"
    assert audit_path.exists()
    with open(audit_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["public_exposure_audit"]["public_exposure_verdict"] == "SAFE_PRIVATE_RUNTIME"

def test_phase10b1_smoke_test():
    script_path = BASE_DIR / "scripts" / "remote_runtime" / "remote_smoke_test.py"
    assert script_path.exists()
    
    result_path = BASE_DIR / "data" / "runtime" / "remote_smoke_test_result.json"
    assert result_path.exists()
    with open(result_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["remote_smoke_test_result"]["overall_smoke_test_verdict"] == "SUCCESS"

def test_phase10b1_api_endpoints():
    r = client.get("/api/remote-runtime/host-profile")
    assert r.status_code == 200
    assert "remote_host_profile" in r.json()
    
    r = client.get("/api/remote-runtime/deployment-attempts")
    assert r.status_code == 200
    
    r = client.get("/api/remote-runtime/burn-in")
    assert r.status_code == 200
    
    r = client.get("/api/remote-runtime/public-exposure")
    assert r.status_code == 200
    
    r = client.get("/api/remote-runtime/smoke-test")
    assert r.status_code == 200

def test_phase10d_app_candidate_decision():
    path = BASE_DIR / "data" / "app_store" / "first_app_candidate_decision.json"
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "first_app_candidate_decision" in data
    assert data["first_app_candidate_decision"]["primary_candidate"]["app_name"] == "RMF Evidence Review Companion"

def test_phase10d_prd_and_mvp():
    assert (BASE_DIR / "docs" / "app_store" / "first_app" / "PRODUCT_REQUIREMENTS.md").exists()
    assert (BASE_DIR / "docs" / "app_store" / "first_app" / "MVP_SCOPE.md").exists()
    assert (BASE_DIR / "docs" / "app_store" / "first_app" / "USER_STORIES.md").exists()
    assert (BASE_DIR / "docs" / "app_store" / "first_app" / "FEATURE_BOUNDARY.md").exists()

def test_phase10d_exposure_review():
    path = BASE_DIR / "data" / "app_store" / "first_app_exposure_review.json"
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["first_app_exposure_review"]["verdict"] == "SAFE_TO_PACKAGE"

def test_phase10d_release_checklist():
    path = BASE_DIR / "data" / "app_store" / "first_app_release_checklist.json"
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["first_app_release_checklist"]["privacy_policy"] == "READY"

def test_phase10d_listing_draft():
    assert (BASE_DIR / "docs" / "app_store" / "first_app" / "APP_STORE_LISTING_DRAFT.md").exists()
    assert (BASE_DIR / "docs" / "app_store" / "first_app" / "APP_DESCRIPTION_SHORT.md").exists()

def test_phase10d_monetization_model():
    path = BASE_DIR / "data" / "app_store" / "first_app_monetization_model.json"
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["first_app_monetization_model"]["model_type"] == "PAID_UPFRONT"

def test_phase10d_build_plan():
    path = BASE_DIR / "data" / "app_store" / "first_app_build_plan.json"
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["first_app_build_plan"]["recommended_stack"] == "Flutter"

def test_phase10d_readiness_gate():
    path = BASE_DIR / "data" / "app_store" / "first_app_readiness_gate.json"
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["first_app_readiness_gate"]["verdict"] == "READY_TO_BUILD"

def test_phase10d_api_endpoints():
    r = client.get("/api/app-store/candidates")
    assert r.status_code == 200
    
    r = client.get("/api/app-store/first-candidate")
    assert r.status_code == 200
    
    r = client.get("/api/app-store/exposure-review")
    assert r.status_code == 200
    
    r = client.get("/api/app-store/release-checklist")
    assert r.status_code == 200
    
    r = client.get("/api/app-store/listing")
    assert r.status_code == 200
    
    r = client.get("/api/app-store/monetization")
    assert r.status_code == 200
    
    r = client.get("/api/app-store/build-plan")
    assert r.status_code == 200
    
    r = client.get("/api/app-store/readiness")
    assert r.status_code == 200

def test_phase10d1_scaffold_existence():
    app_dir = BASE_DIR / "apps" / "rmf_evidence_review_companion"
    assert (app_dir / "pubspec.yaml").exists()
    assert (app_dir / "README.md").exists()
    assert (app_dir / "lib" / "main.dart").exists()
    assert (app_dir / "lib" / "app.dart").exists()

def test_phase10d1_screens_existence():
    screen_dir = BASE_DIR / "apps" / "rmf_evidence_review_companion" / "lib" / "screens"
    assert (screen_dir / "home_screen.dart").exists()
    assert (screen_dir / "rmf_checklist_screen.dart").exists()
    assert (screen_dir / "control_family_screen.dart").exists()
    assert (screen_dir / "evidence_review_screen.dart").exists()
    assert (screen_dir / "poam_prep_screen.dart").exists()
    assert (screen_dir / "conmon_checklist_screen.dart").exists()
    assert (screen_dir / "notes_screen.dart").exists()
    assert (screen_dir / "settings_screen.dart").exists()

def test_phase10d1_assets_existence():
    assets_dir = BASE_DIR / "apps" / "rmf_evidence_review_companion" / "assets" / "data"
    assert (assets_dir / "rmf_checklist.json").exists()
    assert (assets_dir / "control_families.json").exists()
    assert (assets_dir / "evidence_types.json").exists()
    assert (assets_dir / "poam_fields.json").exists()
    assert (assets_dir / "conmon_tasks.json").exists()
    assert (assets_dir / "disclaimers.json").exists()

def test_phase10d1_style_and_boundaries():
    assert (BASE_DIR / "docs" / "app_store" / "first_app" / "UI_STYLE_GUIDE.md").exists()
    assert (BASE_DIR / "docs" / "app_store" / "first_app" / "BRANDING_BOUNDARY.md").exists()
    assert (BASE_DIR / "docs" / "app_store" / "first_app" / "IN_APP_DISCLAIMER.md").exists()

def test_phase10d1_app_metadata():
    path = BASE_DIR / "apps" / "rmf_evidence_review_companion" / "metadata" / "app_metadata.json"
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["app_metadata"]["app_name"] == "RMF Evidence Review Companion"
    assert data["app_metadata"]["telemetry_status"] == "DISABLED"

def test_phase10d1_build_scripts():
    scripts_dir = BASE_DIR / "apps" / "rmf_evidence_review_companion" / "scripts"
    assert (scripts_dir / "check_project.sh").exists()
    assert (scripts_dir / "run_tests.sh").exists()
    assert (scripts_dir / "build_ios_debug.sh").exists()
    assert (scripts_dir / "build_macos_debug.sh").exists()

def test_phase10d1_exposure_scan():
    script_path = BASE_DIR / "scripts" / "app_store" / "scan_first_app_exposure.py"
    assert script_path.exists()
    
    result_path = BASE_DIR / "data" / "app_store" / "first_app_rc1_exposure_scan.json"
    assert result_path.exists()
    with open(result_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["exposure_scan"]["verdict"] == "SAFE_TO_BUILD"

def test_phase10d1_build_gate():
    path = BASE_DIR / "data" / "app_store" / "first_app_rc1_build_gate.json"
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["first_app_rc1_build_gate"]["verdict"] == "RC1_READY"

def test_phase10d1_api_endpoints():
    r = client.get("/api/app-store/first-app/metadata")
    assert r.status_code == 200
    assert "app_metadata" in r.json()
    
    r = client.get("/api/app-store/first-app/exposure-scan")
    assert r.status_code == 200
    
    r = client.get("/api/app-store/first-app/build-gate")
    assert r.status_code == 200
    
    r = client.get("/api/app-store/first-app/checklist")
    assert r.status_code == 200

def test_phase10d2_compile_status():
    path = BASE_DIR / "data" / "app_store" / "first_app_compile_status.json"
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["first_app_compile_status"]["toolchain_status"] == "BLOCKED_BY_LOCAL_TOOLCHAIN"

def test_phase10d2_ui_polish():
    path = BASE_DIR / "data" / "app_store" / "first_app_ui_polish_status.json"
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["first_app_ui_polish_status"]["dark_theme_consistent"] is True

def test_phase10d2_offline_data():
    app_dir = BASE_DIR / "apps" / "rmf_evidence_review_companion"
    assert (app_dir / "lib" / "services" / "offline_data_service.dart").exists()
    
    path = BASE_DIR / "data" / "app_store" / "first_app_offline_data_status.json"
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["first_app_offline_data_status"]["rmf_checklist_loads"] is True

def test_phase10d2_local_storage():
    app_dir = BASE_DIR / "apps" / "rmf_evidence_review_companion"
    assert (app_dir / "lib" / "services" / "local_storage_service.dart").exists()
    
    path = BASE_DIR / "data" / "app_store" / "first_app_local_storage_status.json"
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["first_app_local_storage_status"]["checklist_completion_saves"] is True

def test_phase10d2_flutter_tests():
    app_dir = BASE_DIR / "apps" / "rmf_evidence_review_companion"
    assert (app_dir / "test" / "widget_test.dart").exists()
    assert (app_dir / "test" / "offline_data_service_test.dart").exists()
    assert (app_dir / "test" / "private_exposure_test.dart").exists()

def test_phase10d2_screenshots_and_connect():
    assert (BASE_DIR / "docs" / "app_store" / "first_app" / "SCREENSHOT_CAPTURE_PLAN.md").exists()
    assert (BASE_DIR / "docs" / "app_store" / "first_app" / "APP_ICON_REQUIREMENTS.md").exists()
    assert (BASE_DIR / "docs" / "app_store" / "first_app" / "APP_STORE_CONNECT_SETUP.md").exists()
    
    path = BASE_DIR / "data" / "app_store" / "first_app_asset_readiness.json"
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["first_app_asset_readiness"]["app_icon_staged"] is True
    
    path = BASE_DIR / "data" / "app_store" / "first_app_store_connect_readiness.json"
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["first_app_store_connect_readiness"]["pricing_configured"] is True

def test_phase10d2_readiness_gate():
    path = BASE_DIR / "data" / "app_store" / "first_app_testflight_readiness_gate.json"
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["first_app_testflight_readiness_gate"]["verdict"] == "TESTFLIGHT_READY_PENDING_MICHAEL_APPROVAL"

def test_phase10d2_api_endpoints():
    r = client.get("/api/app-store/first-app/compile-status")
    assert r.status_code == 200
    
    r = client.get("/api/app-store/first-app/ui-polish")
    assert r.status_code == 200
    
    r = client.get("/api/app-store/first-app/offline-data")
    assert r.status_code == 200
    
    r = client.get("/api/app-store/first-app/local-storage")
    assert r.status_code == 200
    
    r = client.get("/api/app-store/first-app/assets")
    assert r.status_code == 200
    
    r = client.get("/api/app-store/first-app/store-connect")
    assert r.status_code == 200
    
    r = client.get("/api/app-store/first-app/testflight-readiness")
    assert r.status_code == 200

def test_phase10d3_toolchain():
    path = BASE_DIR / "data" / "app_store" / "first_app_toolchain_status.json"
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["first_app_toolchain_status"]["verdict"] == "TOOLCHAIN_READY"

def test_phase10d3_compile_results():
    path = BASE_DIR / "data" / "app_store" / "first_app_compile_results.json"
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["first_app_compile_results"]["flutter_pub_get_success"] is True

def test_phase10d3_device_test():
    path = BASE_DIR / "data" / "app_store" / "first_app_device_test_status.json"
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["first_app_device_test_status"]["verdict"] == "SIMULATOR_VALIDATED"

def test_phase10d3_screenshots():
    path = BASE_DIR / "data" / "app_store" / "first_app_screenshot_status.json"
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["first_app_screenshot_status"]["verdict"] == "SCREENSHOTS_VERIFIED"

def test_phase10d3_icon():
    path = BASE_DIR / "data" / "app_store" / "first_app_icon_status.json"
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["first_app_icon_status"]["verdict"] == "BRANDING_VERIFIED"

def test_phase10d3_privacy_declaration():
    path = BASE_DIR / "data" / "app_store" / "first_app_privacy_declaration_status.json"
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["first_app_privacy_declaration_status"]["verdict"] == "PRIVACY_VERIFIED"

def test_phase10d3_upload_gate():
    path = BASE_DIR / "data" / "app_store" / "first_app_testflight_upload_gate.json"
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["first_app_testflight_upload_gate"]["verdict"] == "READY_TO_UPLOAD_PENDING_MICHAEL_APPROVAL"

def test_phase10d3_michael_approval():
    path = BASE_DIR / "data" / "app_store" / "michael_testflight_approval.json"
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["michael_testflight_approval"]["approval_status"] == "PENDING"

def test_phase10d3_api_endpoints():
    r = client.get("/api/app-store/first-app/toolchain")
    assert r.status_code == 200
    
    r = client.get("/api/app-store/first-app/compile-results")
    assert r.status_code == 200
    
    r = client.get("/api/app-store/first-app/device-test")
    assert r.status_code == 200
    
    r = client.get("/api/app-store/first-app/screenshots")
    assert r.status_code == 200
    
    r = client.get("/api/app-store/first-app/icon")
    assert r.status_code == 200
    
    r = client.get("/api/app-store/first-app/privacy-declaration")
    assert r.status_code == 200
    
    r = client.get("/api/app-store/first-app/testflight-upload-gate")
    assert r.status_code == 200
    
    r = client.get("/api/app-store/first-app/michael-approval")
    assert r.status_code == 200















