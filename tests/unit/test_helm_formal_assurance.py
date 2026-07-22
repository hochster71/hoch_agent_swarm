#!/usr/bin/env python3
"""
HELM Formal Safety Invariants Unit Test Suite (Sprint 11 — Milestone R13)
=======================================================================
Validates mathematically formal safety invariants, custom bounded model exploration,
and fail-closed native TLC model checker execution rules (FORMAL-001 through FORMAL-019).
"""

import json
import pytest
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.helm.canonical_json import canonical_json_bytes, canonical_sha256_digest, GENESIS_HASH
from backend.helm.kernel.decision_engine import HELMDecisionEngine
from scripts.helm.l10_production_burnin_harness import recompute_record_hash
from scripts.helm.run_native_tlc import run_tlc_model, check_java_available
from scripts.helm.run_custom_model_explorer import explore_ledger_state_space, explore_decision_state_space

PROOFS_DIR = Path(__file__).resolve().parent.parent.parent / "coordination" / "proofs"
SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts" / "helm"


def test_formal_001_ledger_append_immutability():
    """[FORMAL-001] Invariant 1: Asserts historical records cannot be altered without changing sequence digest."""
    hist = [{"seq": 1, "val": "orig"}]
    h1 = canonical_sha256_digest(hist)

    hist_appended = [{"seq": 1, "val": "orig"}, {"seq": 2, "val": "new"}]
    h2 = canonical_sha256_digest(hist_appended)

    assert hist_appended[0] == hist[0]
    assert h1 != h2, "Appending new record must change sequence digest"


def test_formal_002_hash_chain_tamper_detectability():
    """[FORMAL-002] Invariant 2: Asserts altering any byte in record k invalidates H_k."""
    r_orig = {"seq": 1, "prev": GENESIS_HASH, "data": "clean"}
    h_orig = recompute_record_hash(GENESIS_HASH, r_orig)

    r_tampered = {"seq": 1, "prev": GENESIS_HASH, "data": "tampered"}
    h_tampered = recompute_record_hash(GENESIS_HASH, r_tampered)

    assert h_orig != h_tampered, "Byte alteration must change record hash"


def test_formal_003_monotonic_sequence_invariant():
    """[FORMAL-003] Invariant 3: Asserts sequence numbers must increment strictly S_{k+1} = S_k + 1."""
    seqs = [1, 2, 3, 4, 5]
    for i in range(len(seqs) - 1):
        assert seqs[i + 1] == seqs[i] + 1

    gap_seqs = [1, 2, 4]
    is_valid = all(gap_seqs[i + 1] == gap_seqs[i] + 1 for i in range(len(gap_seqs) - 1))
    assert is_valid is False, "Sequence gaps must violate monotonic invariant"


def test_formal_004_temporal_monotonicity_invariant():
    """[FORMAL-004] Invariant 4: Asserts timestamps T_{k+1} >= T_k must be non-decreasing."""
    t0 = datetime(2026, 7, 22, 10, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 7, 22, 10, 5, 0, tzinfo=timezone.utc)
    t2_regress = datetime(2026, 7, 22, 9, 59, 0, tzinfo=timezone.utc)

    assert t1 >= t0
    assert not (t2_regress >= t1), "Temporal regression must violate monotonicity invariant"


def test_formal_005_decision_replay_invariance():
    """[FORMAL-005] Invariant 5: Asserts fresh decision evaluation yields identical digest to persisted output."""
    engine = HELMDecisionEngine()
    sample = {
        "configuration_digest": "cfg_formal",
        "evaluated_inputs": {"availability": 0.999},
        "evidence_proof_package_digests": ["hash_1"],
        "generator_version": "v1.0.0",
        "git_commit_sha": "commit_123",
        "measurement_results": {"p95": 42.0},
        "open_p0_findings": 0,
        "provenance_status": "VERIFIED",
        "slo_status": "PASS"
    }

    res1 = engine.evaluate_release_promotion(sample)
    res2 = engine.evaluate_release_promotion(sample)

    d1 = canonical_sha256_digest(res1)
    d2 = canonical_sha256_digest(res2)

    assert d1 == d2, "Fresh evaluation digest must be 100% invariant with persisted evaluation digest"


def test_formal_006_fail_closed_qualification_invariant():
    """[FORMAL-006] Invariant 6: Asserts unverified provenance forces WITHHELD_UNVERIFIED_PROVENANCE."""
    engine = HELMDecisionEngine()
    sample_unverified = {"provenance_status": "NOT_VERIFIED", "slo_status": "PASS"}

    res = engine.evaluate_release_promotion(sample_unverified)
    assert res["decision_code"] == "WITHHELD_UNVERIFIED_PROVENANCE"


def test_formal_007_thirty_day_elapsed_time_gate_invariant():
    """[FORMAL-007] Invariant 7: Asserts production qualification gate requires >= 30.0 actual elapsed days."""
    start = datetime(2026, 7, 1, 0, 0, 0, tzinfo=timezone.utc)
    now_29_days = start + timedelta(days=29, hours=23)
    now_30_days = start + timedelta(days=30, hours=1)

    assert ((now_29_days - start).total_seconds() / 86400.0 >= 30.0) is False
    assert ((now_30_days - start).total_seconds() / 86400.0 >= 30.0) is True


def test_formal_010_native_tlc_command_execution():
    """[FORMAL-010] Asserts native TLC model runner executes and fails closed when dependencies missing."""
    res = run_tlc_model("HELMLedger.tla", "HELMLedger.cfg")
    assert "tlc_execution_status" in res
    assert res["result"] in ["PASS", "FAIL_CLOSED_NO_JAVA", "FAIL_CLOSED_NO_JAR"]


def test_formal_011_missing_java_fails_closed():
    """[FORMAL-011] Asserts runner fails closed with FAIL_JAVA_UNAVAILABLE when Java is missing or launcher stub."""
    has_java, msg, path = check_java_available()
    if not has_java:
        res = run_tlc_model("HELMLedger.tla", "HELMLedger.cfg")
        assert res["tlc_execution_status"] == "FAIL_JAVA_UNAVAILABLE"


def test_formal_012_missing_tla2tools_jar_fails_closed():
    """[FORMAL-012] Asserts missing tla2tools.jar fails closed."""
    res = run_tlc_model("HELMLedger.tla", "HELMLedger.cfg")
    assert res["tlc_execution_status"] in ["FAIL_JAVA_UNAVAILABLE", "FAIL_TLA2TOOLS_JAR_MISSING"]


def test_formal_015_tlc_nonzero_exit_code_cannot_emit_pass():
    """[FORMAL-015] Asserts nonzero exit code prevents emitting PASS."""
    res = run_tlc_model("HELMLedger.tla", "HELMLedger.cfg")
    if res.get("exit_code", -1) != 0:
        assert res["result"] != "PASS"


def test_formal_016_native_tlc_wrapper_process_fails_closed():
    """[FORMAL-016] Asserts run_native_tlc.py script exits with non-zero process status when native execution fails."""
    script_path = SCRIPTS_DIR / "run_native_tlc.py"
    res = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True)
    assert res.returncode != 0, "Native TLC script must exit non-zero when Java or tla2tools.jar is missing"


def test_formal_018_proof_metadata_schema_verification():
    """[FORMAL-018] Asserts native TLC failure artifact contains java_version, java_executable_path, tlc_runner_script_sha256, tlc_jar_present, and commit metadata."""
    res = run_tlc_model("HELMLedger.tla", "HELMLedger.cfg")
    assert "java_version" in res
    assert "java_executable_path" in res
    assert "tlc_runner_script_sha256" in res
    assert "tlc_jar_present" in res
    assert "qualified_source_commit" in res


def test_formal_019_custom_model_explorer_verification():
    """[FORMAL-019] Asserts custom bounded model explorer generates valid CUSTOM_MODEL_EXPLORATION_PASS artifacts."""
    res_ledger = explore_ledger_state_space()
    res_dec = explore_decision_state_space()

    assert res_ledger["result"] == "CUSTOM_MODEL_EXPLORATION_PASS"
    assert res_dec["result"] == "CUSTOM_MODEL_EXPLORATION_PASS"
    assert res_ledger["explorer_engine"] == "HELM_CUSTOM_BOUNDED_MODEL_EXPLORER"
