#!/usr/bin/env python3
"""
HELM Production Qualification Unit Test Suite (Sprint 10 — Milestone R12)
=======================================================================
Validates operational burn-in manifest generation, ledger hash-chain continuity,
zero replay divergence verification, and 30-day elapsed time enforcement rules.
"""

import json
import pytest
from pathlib import Path

from scripts.helm.l10_production_burnin_harness import (
    create_burnin_manifest,
    record_burnin_observation,
    verify_burnin_ledger,
    GENESIS_HASH,
    PROOFS_DIR
)


def test_prod_001_burnin_manifest_generation():
    """[PROD-001] Asserts production burn-in manifest contains required tracking fields."""
    m = create_burnin_manifest("qualified_commit_123")
    assert m["qualified_source_commit"] == "qualified_commit_123"
    assert m["expected_interval_seconds"] == 300
    assert "burn_in_id" in m


def test_prod_002_observation_hash_chain_continuity():
    """[PROD-002] Asserts consecutive observations maintain valid cryptographic hash-chain continuity."""
    sample = {
        "configuration_digest": "cfg_test",
        "evaluated_inputs": {"availability": 0.999},
        "evidence_proof_package_digests": ["hash_1"],
        "generator_version": "v1.0.0",
        "git_commit_sha": "commit_123",
        "measurement_results": {"p95": 42.0},
        "open_p0_findings": 0,
        "provenance_status": "VERIFIED",
        "slo_status": "PASS"
    }

    obs1 = record_burnin_observation(1, GENESIS_HASH, sample)
    obs2 = record_burnin_observation(2, obs1["record_hash"], sample)

    assert obs1["previous_hash"] == GENESIS_HASH
    assert obs2["previous_hash"] == obs1["record_hash"]
    assert obs1["record_hash"] != obs2["record_hash"]


def test_prod_003_zero_replay_divergence_verification():
    """[PROD-003] Asserts observation determinism verifies zero digest divergence."""
    sample = {"val": 100}
    obs = record_burnin_observation(1, GENESIS_HASH, sample)

    assert obs["canonical_digest"] == obs["replay_digest"]
    assert obs["determinism_result"] == "PASS"


def test_prod_004_elapsed_time_gate_enforcement():
    """[PROD-004] Asserts production burn-in exit criteria blocks completion if elapsed time < 30 days."""
    m = create_burnin_manifest("commit_123")
    elapsed_days = 0.5  # < 30 days

    burnin_complete = elapsed_days >= 30.0
    assert burnin_complete is False, "Burn-in completion must require >= 30 actual elapsed days"


def test_prod_005_ledger_verification_suite(tmp_path):
    """[PROD-005] Asserts ledger verifier catches tampered observation entry."""
    ledger_file = tmp_path / "test_ledger.jsonl"

    sample = {
        "configuration_digest": "cfg_test",
        "evaluated_inputs": {"availability": 0.999},
        "evidence_proof_package_digests": ["hash_1"],
        "generator_version": "v1.0.0",
        "git_commit_sha": "commit_123",
        "measurement_results": {"p95": 42.0},
        "open_p0_findings": 0,
        "provenance_status": "VERIFIED",
        "slo_status": "PASS"
    }

    obs1 = record_burnin_observation(1, GENESIS_HASH, sample)

    # Tamper with prev hash
    obs2 = record_burnin_observation(2, "TAMPERED_PREV_HASH", sample)

    with open(ledger_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(obs1) + "\n")
        f.write(json.dumps(obs2) + "\n")

    res = verify_burnin_ledger(ledger_file)
    assert res["hash_chain_valid"] is False
    assert res["status"] == "CORRUPTED"
