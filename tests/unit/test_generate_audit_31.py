import sys
import json
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.generate_audit_31_assurance_case import (
    run_voice_tests,
    inspect_runtime_ledgers,
    generate_assurance_case_md,
    build_voice_assurance_engine,
    inspect_helm_live_runtime_state,
)
from scripts.helm_assurance_engine import (
    HELMAssuranceEngine,
    ClaimNode,
    EvidenceNode,
    EvidenceProvenance,
    AssumptionNode,
    DefeaterNode,
    DefeaterSeverity,
    RequirementNode,
    ControlNode,
    ScopeAlignment,
    EvidenceState,
    ClaimHealth,
    PromotionStatus,
    SharedEvidenceRegistry,
    ReasoningModelSpec,
    evaluate_assurance_manifest,
    verify_closed_loop_ledger_integrity,
    replay_closed_loop_ledger,
    verify_version_compatibility,
    verify_jcs_conformance_vectors,
    LEDGER_RECOVERY_POLICY_DECISION_TABLE,
    CLOSED_LOOP_LEDGER_PATH,
)

def test_generate_audit_31_execution():
    passed, total, ok = run_voice_tests()
    assert ok is True
    assert passed == 72
    assert total == 72

def test_inspect_runtime_ledgers():
    ledgers = inspect_runtime_ledgers()
    assert isinstance(ledgers, dict)
    assert "command_audit_count" in ledgers
    assert "has_local_runtime_evidence" in ledgers

def test_generate_assurance_case_md(tmp_path, monkeypatch):
    target = tmp_path / "HELM_VOICE_RUNTIME_CERTIFICATION_AUDIT_31.md"
    target_json = tmp_path / "HELM_VOICE_RUNTIME_CERTIFICATION_AUDIT_31.json"
    monkeypatch.setattr("scripts.generate_audit_31_assurance_case.OUTPUT_DOC", target)
    monkeypatch.setattr("scripts.generate_audit_31_assurance_case.OUTPUT_JSON", target_json)
    generate_assurance_case_md()
    assert target.exists()
    assert target_json.exists()
    content = target.read_text(encoding="utf-8")
    assert "Audit 31: HELM Voice Living Assurance Case" in content
    assert "72 / 72 passed" in content

def test_assurance_engine_quantitative_scoring():
    live_runtime = inspect_helm_live_runtime_state()
    engine = build_voice_assurance_engine(live_runtime, True)
    
    req = RequirementNode(
        id="REQ-HELM-VOICE-01",
        title="Voice Ingress Authorization",
        description="All voice commands must be sanitized and checked against doorstep policies.",
        source_standard="HELM-ENGINEERING-DOCTRINE-v1",
        associated_claim_ids=["CLAIM-01"],
    )
    engine.add_requirement(req)
    assert "REQ-HELM-VOICE-01" in engine.requirements

    evals = engine.evaluate_all()
    assert "CLAIM-01" in evals
    assert evals["CLAIM-01"]["confidence_score"] == 1.0
    assert evals["CLAIM-01"]["health"] == ClaimHealth.FULL_CONFIDENCE

    # Test critical defeater invalidation
    crit_defeater = DefeaterNode(
        id="DEF-TEST-CRIT",
        description="Critical failure probe",
        evaluator=lambda: (True, "CRITICAL_FAILURE"),
        target_claim_id="CLAIM-01",
        severity=DefeaterSeverity.CRITICAL,
    )
    claim1 = engine.claims[0]
    claim1.defeater_nodes.append(crit_defeater)
    
    crit_eval = claim1.evaluate_health()
    assert crit_eval["health"] == ClaimHealth.INVALIDATED
    assert crit_eval["confidence_score"] == 0.0

def test_shared_evidence_registry():
    registry = SharedEvidenceRegistry()
    ev = EvidenceNode(
        id="EV-SHARED-TEST",
        path=ROOT / "tests" / "unit" / "test_helm_voice_executive.py",
        covered_scope="Voice Gateway",
        excluded_scope="N/A",
        scope_alignment=ScopeAlignment.EXACT_MATCH,
        provenance=EvidenceProvenance("pytest", "sha", "1.0", True),
        weight=0.9,
    )
    registry.register(ev)
    fetched = registry.get("EV-SHARED-TEST")
    assert fetched is not None
    assert fetched.weight == 0.9

def test_canonical_manifest_relationships_and_api():
    live_runtime = inspect_helm_live_runtime_state()
    engine = build_voice_assurance_engine(live_runtime, True)
    manifest = evaluate_assurance_manifest(engine)
    
    assert "metadata" in manifest
    assert manifest["metadata"]["reasoning_model"]["version"] == "2.2"
    assert manifest["metadata"]["reasoning_model"]["spec_status"] == "REASONING_SPEC_FROZEN_PENDING_SYSTEM_INTEGRATION"
    assert manifest["metadata"]["reasoning_model"]["canonicalization"]["spec"] == "RFC8785"
    assert manifest["metadata"]["reasoning_model"]["canonicalization"]["implementation"] == "helm-jcs"
    assert manifest["metadata"]["reasoning_model"]["canonicalization"]["build"]["git_commit"].startswith("c40f5da")
    assert manifest["metadata"]["reasoning_model"]["canonicalization"]["build"]["git_short"] == "c40f5da"
    assert "evaluation" in manifest
    assert "status" in manifest["evaluation"]
    assert "promotion_authorization" in manifest["evaluation"]
    assert "technical_authorization" in manifest["evaluation"]["promotion_authorization"]
    assert "operational_authorization" in manifest["evaluation"]["promotion_authorization"]
    assert "provenance" in manifest["evaluation"]
    assert "graph_manifest_sha256" in manifest["evaluation"]["provenance"]
    assert "evaluation_digest_sha256" in manifest["evaluation"]["provenance"]
    assert "relationships" in manifest
    
    rels = manifest["relationships"]
    assert len(rels) > 0
    rel_types = set(r["type"] for r in rels)
    assert "implements" in rel_types
    assert "supports" in rel_types
    assert "verified_by" in rel_types

    # Assert explanation traces ('because_structured' arrays with depends_on_steps & depends_on_nodes) exist
    claim1 = manifest["claims"][0]
    assert "because_structured" in claim1
    assert len(claim1["because_structured"]) > 0
    step1 = claim1["because_structured"][0]
    assert "type" in step1
    assert "node_id" in step1
    assert "depends_on_steps" in step1
    assert "depends_on_nodes" in step1

    # Find an INFERENCE step and verify non-empty depends_on_nodes list
    inference_steps = [s for s in claim1["because_structured"] if s["type"] == "INFERENCE"]
    assert len(inference_steps) > 0
    assert len(inference_steps[0]["depends_on_nodes"]) > 0
    assert "EV-PYTEST" in inference_steps[0]["depends_on_nodes"]

def test_counterfactual_and_graph_analysis_apis():
    live_runtime = inspect_helm_live_runtime_state()
    engine = build_voice_assurance_engine(live_runtime, True)
    
    # 1. Counterfactual impact simulation
    sim_impact = engine.simulate_counterfactual(
        stale_evidence_ids=["EV-PYTEST"],
        triggered_defeater_ids=["DEF-01"],
    )
    assert "counterfactual" in sim_impact
    assert "impact" in sim_impact
    assert "explanation" in sim_impact
    assert sim_impact["impact"]["affected_claims_count"] > 0
    assert "CLAIM-01" in sim_impact["impact"]["affected_claim_ids"]
    assert sim_impact["explanation"]["simulation_results"]["CLAIM-01"]["simulated_health"] == ClaimHealth.INVALIDATED

    # 2. Minimal-cut analysis
    min_cut = engine.analyze_minimal_cut("CLAIM-01")
    assert "single_point_invalidation_defeaters" in min_cut
    assert "DEF-01" in min_cut["single_point_invalidation_defeaters"]
    assert "EV-PYTEST" in min_cut["single_point_degradation_nodes"]

    # 3. Node influence ranking
    rankings = engine.analyze_node_influence()
    assert len(rankings) > 0
    top_node = rankings[0]
    assert "node_id" in top_node
    assert "dependent_claim_count" in top_node

def test_assurance_work_optimization_and_heatmap_apis():
    live_runtime = inspect_helm_live_runtime_state()
    engine = build_voice_assurance_engine(live_runtime, True)

    # 1. Heat map generation
    heatmap = engine.generate_assurance_heatmap()
    assert "total_nodes_analyzed" in heatmap
    assert "heatmap_nodes" in heatmap
    assert len(heatmap["heatmap_nodes"]) > 0
    assert "criticality_score" in heatmap["heatmap_nodes"][0]

    # 2. Work backlog recommendation engine (v2.2 risk-aware)
    backlog_res = engine.recommend_assurance_work_backlog()
    assert "recommendations_count" in backlog_res
    assert "recommended_backlog" in backlog_res
    assert len(backlog_res["recommended_backlog"]) > 0
    top_recommendation = backlog_res["recommended_backlog"][0]
    assert "rank" in top_recommendation
    assert top_recommendation["rank"] == 1
    assert "priority_score" in top_recommendation

    # 3. Enriched Swarm task export API
    swarm_export = engine.export_swarm_task_assignments()
    assert "total_tasks_assigned" in swarm_export
    assert "swarm_tasks" in swarm_export
    assert len(swarm_export["swarm_tasks"]) > 0
    task1 = swarm_export["swarm_tasks"][0]
    assert "task_id" in task1
    assert "assigned_swarm" in task1

def test_closed_loop_execution_ledger_hash_chaining_and_replay_api(tmp_path):
    live_runtime = inspect_helm_live_runtime_state()
    engine = build_voice_assurance_engine(live_runtime, True)

    # Test Dual Promotion Authorization Gate (Technical & Operational)
    promo_gate = engine.evaluate_promotion_authorization()
    assert "technical_authorization" in promo_gate
    assert "operational_authorization" in promo_gate
    assert promo_gate["operational_authorization"]["founder_gate_required"] is True

    # Test Closed-Loop Transaction with Hash Chaining
    test_art = tmp_path / "closed_loop_v22_art.json"
    res = engine.execute_closed_loop_update(produced_artifacts=[str(test_art)])

    assert res["transaction_status"] == "SUCCESS"
    assert "transaction_id" in res
    assert "previous_transaction_hash" in res
    assert "current_transaction_hash" in res
    assert CLOSED_LOOP_LEDGER_PATH.exists()

    # Test Audit Tooling for Ledger Integrity Verification
    audit_res = verify_closed_loop_ledger_integrity()
    assert audit_res["status"] == "VERIFIED_INTEGRITY"

    # Test Deterministic Ledger Replay Tooling
    replay_res = replay_closed_loop_ledger()
    assert replay_res["replay_status"] == "DETERMINISTIC_REPLAY_SUCCESS"
    assert replay_res["total_chained_transactions"] > 0
    assert replay_res["verified_policy_version"] == "2.2"
    assert replay_res["verified_canonicalization"]["spec"] == "RFC8785"
    assert replay_res["verified_canonicalization"]["implementation"] == "helm-jcs"
    assert replay_res["verified_canonicalization"]["build"]["git_commit"].startswith("c40f5da")
    assert replay_res["verified_canonicalization"]["build"]["git_short"] == "c40f5da"

def test_negative_replay_fault_injection(tmp_path):
    """Negative fault-injection test suite verifying tamper-evident detection across corrupted hashes, broken chains, and reordered transactions."""
    live_runtime = inspect_helm_live_runtime_state()
    engine = build_voice_assurance_engine(live_runtime, True)

    # Generate 2 valid transactions on a isolated test ledger file
    test_ledger = tmp_path / "test_fault_ledger.jsonl"
    
    # Run 2 updates temporarily targeting test_ledger
    art1 = tmp_path / "art1.json"
    art2 = tmp_path / "art2.json"
    
    # Save original ledger path
    import scripts.helm_assurance_engine as hae
    orig_path = hae.CLOSED_LOOP_LEDGER_PATH
    try:
        hae.CLOSED_LOOP_LEDGER_PATH = test_ledger
        engine.execute_closed_loop_update(produced_artifacts=[str(art1)])
        engine.execute_closed_loop_update(produced_artifacts=[str(art2)])

        # 1. Baseline replay should succeed
        baseline = replay_closed_loop_ledger(test_ledger)
        assert baseline["replay_status"] == "DETERMINISTIC_REPLAY_SUCCESS"
        assert baseline["total_chained_transactions"] == 2

        # 2. Inject Corrupted Evaluation Digest in Step 2 -> Expect HASH_COMPUTATION_MISMATCH_ERROR
        records = [json.loads(line) for line in test_ledger.read_text().splitlines() if line.strip()]
        corrupted_digest_records = [dict(r) for r in records]
        corrupted_digest_records[1]["evaluation_digest_sha256"] = "deadbeef1234567890abcdef"
        
        corrupted_ledger_1 = tmp_path / "corrupted_digest.jsonl"
        corrupted_ledger_1.write_text("\n".join([json.dumps(r) for r in corrupted_digest_records]) + "\n")
        
        res1 = replay_closed_loop_ledger(corrupted_ledger_1)
        assert res1["replay_status"] == "HASH_COMPUTATION_MISMATCH_ERROR"

        # 3. Inject Broken Previous Hash in Step 2 -> Expect HASH_CHAIN_DISCONTINUITY_ERROR
        discontinuous_records = [dict(r) for r in records]
        discontinuous_records[1]["previous_transaction_hash"] = "invalid_previous_hash_value"
        
        corrupted_ledger_2 = tmp_path / "discontinuous.jsonl"
        corrupted_ledger_2.write_text("\n".join([json.dumps(r) for r in discontinuous_records]) + "\n")

        res2 = replay_closed_loop_ledger(corrupted_ledger_2)
        assert res2["replay_status"] == "HASH_CHAIN_DISCONTINUITY_ERROR"

        # 4. Reorder Transactions (Step 2 before Step 1) -> Expect HASH_CHAIN_DISCONTINUITY_ERROR
        reordered_records = [records[1], records[0]]
        reordered_ledger = tmp_path / "reordered.jsonl"
        reordered_ledger.write_text("\n".join([json.dumps(r) for r in reordered_records]) + "\n")

        res3 = replay_closed_loop_ledger(reordered_ledger)
        assert res3["replay_status"] == "HASH_CHAIN_DISCONTINUITY_ERROR"
    finally:
        hae.CLOSED_LOOP_LEDGER_PATH = orig_path

def test_version_compatibility_verification():
    """Unit test for fail-closed version compatibility verification across rich state taxonomy and feature flag requirements."""
    # 1. Compatible v2.2 manifest
    valid_data = {"metadata": {"reasoning_model": {"version": "2.2", "feature_flags": ["hash_chain_v4", "dual_authorization_v3"]}}}
    comp1 = verify_version_compatibility(valid_data)
    assert comp1["compatibility"] == "COMPATIBLE"

    # 2. Forward compatible limited (v2.5) -> FORWARD_COMPATIBLE_LIMITED
    fwd_data = {"metadata": {"reasoning_model": {"version": "2.5", "feature_flags": ["hash_chain_v4"]}}}
    comp_fwd = verify_version_compatibility(fwd_data)
    assert comp_fwd["compatibility"] == "FORWARD_COMPATIBLE_LIMITED"

    # 3. Backward compatible (v2.1) -> BACKWARD_COMPATIBLE
    bwd_data = {"metadata": {"reasoning_model": {"version": "2.1", "feature_flags": ["hash_chain_v4"]}}}
    comp_bwd = verify_version_compatibility(bwd_data)
    assert comp_bwd["compatibility"] == "BACKWARD_COMPATIBLE"

    # 4. Incompatible v3.0 manifest -> fail closed
    incompatible_data = {"metadata": {"reasoning_model": {"version": "3.0"}}}
    comp2 = verify_version_compatibility(incompatible_data)
    assert comp2["compatibility"] == "INCOMPATIBLE_FAIL_CLOSED"
    assert "outside supported range" in comp2["reason"]

    # 5. Missing required feature flag -> fail closed
    comp_flag = verify_version_compatibility(valid_data, required_feature_flags=["missing_custom_flag_v1"])
    assert comp_flag["compatibility"] == "INCOMPATIBLE_FAIL_CLOSED"
    assert "Missing required feature flag" in comp_flag["reason"]

    # 6. Unparseable version string -> fail closed
    invalid_data = {"metadata": {"reasoning_model": {"version": "invalid_v"}}}
    comp3 = verify_version_compatibility(invalid_data)
    assert comp3["compatibility"] == "INCOMPATIBLE_FAIL_CLOSED"

def test_jcs_conformance_vectors():
    """Unit test for RFC 8785 JSON Canonicalization Scheme (JCS) test corpus verification."""
    res = verify_jcs_conformance_vectors()
    assert res["status"] == "CONFORMANCE_VERIFIED"
    assert res["passed_vectors"] == res["total_vectors"]
    assert res["total_vectors"] == 10
    assert res["positive_vectors_count"] == 7
    assert res["negative_vectors_count"] == 3
    assert res["implementation"] == "helm-jcs"
    assert "computed_canonical_str" in res["vector_results"][0]

def test_concurrent_append_locking_and_replay_validation(tmp_path):
    """Multi-threaded concurrent append: flock serializes writers in one process.

    Valuable regression, but not final concurrency proof — threads share an address
    space. Multi-process test (below) exercises the deployment model flock is for.
    """
    import concurrent.futures
    import scripts.helm_assurance_engine as hae
    from scripts.helm_assurance_engine import HELMAssuranceEngine, verify_closed_loop_ledger_integrity, replay_closed_loop_ledger

    test_ledger = tmp_path / "concurrent_ledger.jsonl"
    art_dir = tmp_path / "arts"
    art_dir.mkdir()
    orig_path = hae.CLOSED_LOOP_LEDGER_PATH
    hae.CLOSED_LOOP_LEDGER_PATH = test_ledger

    try:
        engine = HELMAssuranceEngine(
            title="Concurrent Ledger Test",
            artifact_id="AUDIT-TEST-CONCURRENT",
            scope="test/concurrent"
        )

        def append_transaction(worker_idx):
            engine.execute_closed_loop_update(
                worker_id=f"worker-thread-{worker_idx}",
                produced_artifacts=[str(art_dir / f"artifact_{worker_idx}.txt")],
            )

        # Run 20 concurrent worker threads appending simultaneously
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(append_transaction, i) for i in range(20)]
            concurrent.futures.wait(futures)

        # Verify ledger file line count and line completeness
        lines = test_ledger.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 20

        # Verify integrity and replay across all concurrent entries
        integrity = verify_closed_loop_ledger_integrity(ledger_path=test_ledger)
        assert integrity["status"] == "VERIFIED_INTEGRITY"
        assert integrity["valid_transactions"] == 20
        assert integrity["chain_verified"] is True

        replay = replay_closed_loop_ledger(ledger_path=test_ledger)
        assert replay["replay_status"] == "DETERMINISTIC_REPLAY_SUCCESS"
        assert replay["total_chained_transactions"] == 20
    finally:
        hae.CLOSED_LOOP_LEDGER_PATH = orig_path

def _mp_append_worker(test_ledger_path: str, art_dir: str, worker_idx: int, appends: int):
    """OS process worker: production append API against shared ledger (same locking protocol)."""
    from pathlib import Path
    import scripts.helm_assurance_engine as hae
    from scripts.helm_assurance_engine import HELMAssuranceEngine

    hae.CLOSED_LOOP_LEDGER_PATH = Path(test_ledger_path)
    engine = HELMAssuranceEngine(
        title="Multi-Process Ledger Test",
        artifact_id="AUDIT-TEST-MULTIPROCESS",
        scope="test/multiprocess"
    )
    for j in range(appends):
        engine.execute_closed_loop_update(
            worker_id=f"worker-process-{worker_idx}-a{j}",
            produced_artifacts=[str(Path(art_dir) / f"mp_{worker_idx}_{j}.txt")],
        )

def test_multiprocess_concurrent_append_locking_and_replay(tmp_path):
    """Multi-process contention: N independent Python processes, same ledger + append API.

    This is the deployment model advisory flock/fcntl is designed for — not threads.
    Verifies: expected count, unique tx ids, continuous hash chain, deterministic
    replay, no malformed JSONL lines.
    """
    import json
    import multiprocessing
    import scripts.helm_assurance_engine as hae
    from scripts.helm_assurance_engine import verify_closed_loop_ledger_integrity, replay_closed_loop_ledger

    test_ledger = tmp_path / "multiprocess_ledger.jsonl"
    art_dir = tmp_path / "mp_arts"
    art_dir.mkdir()
    n_processes = 16
    m_appends = 3
    expected = n_processes * m_appends
    orig_path = hae.CLOSED_LOOP_LEDGER_PATH
    hae.CLOSED_LOOP_LEDGER_PATH = test_ledger

    try:
        processes = []
        for i in range(n_processes):
            p = multiprocessing.Process(
                target=_mp_append_worker,
                args=(str(test_ledger), str(art_dir), i, m_appends),
            )
            processes.append(p)
            p.start()

        for p in processes:
            p.join(timeout=60)
            assert p.exitcode == 0, f"worker exitcode={p.exitcode}"

        raw_lines = [ln for ln in test_ledger.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert len(raw_lines) == expected

        records = []
        for ln in raw_lines:
            rec = json.loads(ln)  # no malformed JSONL
            records.append(rec)

        tx_ids = [r["transaction_id"] for r in records]
        assert len(tx_ids) == len(set(tx_ids)), "duplicate transaction_id"

        prev = "GENESIS_ROOT"
        for i, r in enumerate(records):
            assert r["previous_transaction_hash"] == prev, f"gap/fork at {i}"
            prev = r["current_transaction_hash"]

        integrity = verify_closed_loop_ledger_integrity(ledger_path=test_ledger)
        assert integrity["status"] == "VERIFIED_INTEGRITY"
        assert integrity["valid_transactions"] == expected
        assert integrity["chain_verified"] is True
        assert not integrity.get("parse_errors")

        replay = replay_closed_loop_ledger(ledger_path=test_ledger)
        assert replay["replay_status"] == "DETERMINISTIC_REPLAY_SUCCESS"
        assert replay["total_chained_transactions"] == expected
        assert replay["head_transaction_hash"] == records[-1]["current_transaction_hash"]
    finally:
        hae.CLOSED_LOOP_LEDGER_PATH = orig_path

def test_high_scale_burn_in_and_crash_recovery(tmp_path):
    """High-scale operational burn-in test: appends 100 high-frequency transactions, verifies lock contention stability, hash chain continuity, and clean recovery."""
    import time
    import scripts.helm_assurance_engine as hae
    from scripts.helm_assurance_engine import HELMAssuranceEngine, verify_closed_loop_ledger_integrity, replay_closed_loop_ledger

    test_ledger = tmp_path / "burn_in_ledger.jsonl"
    orig_path = hae.CLOSED_LOOP_LEDGER_PATH
    hae.CLOSED_LOOP_LEDGER_PATH = test_ledger

    try:
        engine = HELMAssuranceEngine(
            title="Operational Burn-In Test",
            artifact_id="AUDIT-TEST-BURNIN-100",
            scope="test/burnin"
        )

        start_time = time.time()
        for i in range(100):
            engine.execute_closed_loop_update(
                worker_id=f"burn-in-worker-{i % 5}",
                produced_artifacts=[f"burnin_art_{i}.txt"]
            )
        elapsed = time.time() - start_time

        # Verify record count
        lines = [ln for ln in test_ledger.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert len(lines) == 100

        # Verify integrity & deterministic replay
        integrity = verify_closed_loop_ledger_integrity(ledger_path=test_ledger)
        assert integrity["status"] == "VERIFIED_INTEGRITY"
        assert integrity["valid_transactions"] == 100

        replay = replay_closed_loop_ledger(ledger_path=test_ledger)
        assert replay["replay_status"] == "DETERMINISTIC_REPLAY_SUCCESS"
        assert replay["total_chained_transactions"] == 100
        assert elapsed < 15.0  # High throughput requirement (<15s for 100 locked appends + fsync)
    finally:
        hae.CLOSED_LOOP_LEDGER_PATH = orig_path

def test_interrupted_write_recovery(tmp_path):
    """Interrupted write / crash recovery test: verifies that ledger append and reader engines gracefully recover when a truncated/corrupted line exists at the end of the file."""
    import scripts.helm_assurance_engine as hae
    from scripts.helm_assurance_engine import HELMAssuranceEngine, load_closed_loop_ledger_records

    test_ledger = tmp_path / "crash_ledger.jsonl"
    orig_path = hae.CLOSED_LOOP_LEDGER_PATH
    hae.CLOSED_LOOP_LEDGER_PATH = test_ledger

    try:
        engine = HELMAssuranceEngine(
            title="Crash Recovery Test",
            artifact_id="AUDIT-TEST-CRASH-RECOVERY",
            scope="test/crash"
        )

        # 1. Write 3 valid records
        for i in range(3):
            engine.execute_closed_loop_update(
                worker_id=f"worker-precrash-{i}",
                produced_artifacts=[f"precrash_{i}.txt"]
            )

        # 2. Simulate process crash by writing an incomplete/truncated JSON line to the file
        with open(test_ledger, "a", encoding="utf-8") as f:
            f.write('{"transaction_id": "TX-CRASH-INCOMPLETE", "previous_transaction_hash": "corrupted_incomplete_bytes')

        # 3. Read ledger under non-strict mode: load_closed_loop_ledger_records recovers valid records and isolates parse error
        loaded = load_closed_loop_ledger_records(test_ledger, fail_on_malformed=False)
        assert len(loaded["records"]) == 3
        assert len(loaded["parse_errors"]) == 1
        assert loaded["parse_errors"][0]["code"] == "MALFORMED_JSONL_LINE"

        # 4. Append new valid transaction: engine recovers by chaining from last valid record
        res_post = engine.execute_closed_loop_update(
            worker_id="worker-postcrash-4",
            produced_artifacts=["postcrash_4.txt"]
        )
        assert res_post["previous_transaction_hash"] == loaded["records"][-1]["current_transaction_hash"]
    finally:
        hae.CLOSED_LOOP_LEDGER_PATH = orig_path

def test_midfile_corruption_rejection(tmp_path):
    """Mid-file corruption test: verifies that if a malformed record exists in the middle of a ledger log file, appends fail closed with MID_FILE_CORRUPTION_REJECTED."""
    import scripts.helm_assurance_engine as hae
    from scripts.helm_assurance_engine import HELMAssuranceEngine

    test_ledger = tmp_path / "midfile_corrupt_ledger.jsonl"
    orig_path = hae.CLOSED_LOOP_LEDGER_PATH
    hae.CLOSED_LOOP_LEDGER_PATH = test_ledger

    try:
        engine = HELMAssuranceEngine(
            title="Midfile Corrupt Test",
            artifact_id="AUDIT-TEST-MIDFILE-CORRUPT",
            scope="test/midfile"
        )

        # 1. Write valid record 1
        engine.execute_closed_loop_update(worker_id="w-1", produced_artifacts=["art_1.txt"])

        # 2. Write corrupted line in the middle of the log file
        with open(test_ledger, "a", encoding="utf-8") as f:
            f.write('{"transaction_id": "CORRUPTED_MIDFILE_BYTES_WITHOUT_CLOSING_BRACKET\n')

        # 3. Write valid record 3 AFTER the corrupted mid-file record
        engine.execute_closed_loop_update(worker_id="w-3", produced_artifacts=["art_3.txt"])

        # 4. Attempt next append: _read_tail_hash_under_lock detects non-final line corruption and fails closed
        res = engine.execute_closed_loop_update(worker_id="w-4", produced_artifacts=["art_4.txt"])
        assert res["transaction_status"] == "LEDGER_APPEND_FAILED"
        assert res["error"]["code"] == "MID_FILE_CORRUPTION_REJECTED"
    finally:
        hae.CLOSED_LOOP_LEDGER_PATH = orig_path

def test_recovery_policy_decision_table():
    """Unit test for operational recovery policy decision table taxonomy and enum validation."""
    from scripts.helm_assurance_engine import POLICY_IMPLEMENTATION_STATE_ALLOWED_VALUES
    assert len(LEDGER_RECOVERY_POLICY_DECISION_TABLE) == 4
    codes = [item["code"] for item in LEDGER_RECOVERY_POLICY_DECISION_TABLE]
    assert "TRUNCATED_FINAL_RECORD_DETECTED" in codes
    assert "MID_FILE_CORRUPTION_REJECTED" in codes
    assert "HASH_CHAIN_DISCONTINUITY_ERROR" in codes
    assert "DUPLICATE_TX_ID_UNENFORCED_OUTSIDE_SCOPE" in codes
    for row in LEDGER_RECOVERY_POLICY_DECISION_TABLE:
        assert "implementation_state" in row
        assert row["implementation_state"] in POLICY_IMPLEMENTATION_STATE_ALLOWED_VALUES
        assert "policy" in row
        assert "result" in row
        assert "code" in row


def test_governance_policy_json_schema_validation():
    """Unit test validating exported governance_policies against formal JSON Schema using jsonschema validator."""
    import importlib.metadata
    import jsonschema
    from scripts.helm_assurance_engine import governance_validation_environment

    schema_path = ROOT / "docs" / "helm" / "schemas" / "governance_policies_schema_v1.json"
    assert schema_path.exists(), "Formal JSON schema file must exist"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert schema.get("additionalProperties") is False

    engine = HELMAssuranceEngine(
        title="Test Audit 31",
        artifact_id="TEST-31",
        scope="Unit Test Scope",
    )
    manifest = engine.export_canonical_manifest()
    gov_policies = manifest["metadata"]["governance_policies"]
    val_env = manifest["metadata"]["governance_validation_environment"]

    # Direct JSON Schema validation using jsonschema library (additionalProperties: false)
    jsonschema.validate(instance=gov_policies, schema=schema)

    # Reproducibility: record validator package version in evidence metadata
    expected_ver = importlib.metadata.version("jsonschema")
    assert val_env["jsonschema_package_version"] == expected_ver
    assert val_env["schema_draft"].endswith("2020-12/schema")
    assert val_env["contract_mode"].startswith("CLOSED_WORLD")
    # Helper matches export
    assert governance_validation_environment()["jsonschema_package_version"] == expected_ver

    # Closed world: unexpected keys rejected
    dirty = dict(gov_policies)
    dirty["not_in_contract"] = True
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=dirty, schema=schema)






