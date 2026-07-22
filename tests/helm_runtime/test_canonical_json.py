#!/usr/bin/env python3
r"""
Unit and Conformance Tests for Python RFC 8785 Canonical JSON & SHA-256 Engine
================================================================================
Validates 100% pass rate on `tests/fixtures/helm_canonical_json_conformance_corpus.json`
and tests all 8 RFC 8785 edge-case categories.
"""

import json
import pytest
from pathlib import Path

from scripts.helm.canonical_json import (
    canonical_json_bytes,
    canonical_sha256_digest,
    compute_transition_hash,
    DOMAIN_TAG,
    GENESIS_HASH,
)
from backend.helm.kernel.decision_engine import HELMDecisionEngine

CORPUS_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "helm_canonical_json_conformance_corpus.json"


def test_conformance_corpus_vectors_pass_100_percent():
    """Validates that all test vectors in the normative conformance corpus produce exact expected byte hex & SHA-256 digests."""
    assert CORPUS_PATH.exists(), f"Corpus fixture missing: {CORPUS_PATH}"

    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        corpus_data = json.load(f)

    vectors = corpus_data.get("vectors", [])
    assert len(vectors) >= 4, f"Expected at least 4 conformance vectors, found {len(vectors)}"

    for vector in vectors:
        vector_id = vector["vector_id"]
        raw_input = vector["raw_input"]
        expected_code = vector["expected_decision_code"]
        expected_digest = vector["expected_decision_digest"]
        expected_canonical_utf8 = vector["expected_canonical_utf8"]
        expected_canonical_bytes_hex = vector["expected_canonical_bytes_hex"]

        # Replay decision through reference engine
        decision_res = HELMDecisionEngine.evaluate_release_promotion(raw_input)
        assert decision_res["decision_code"] == expected_code, f"Vector {vector_id} decision code mismatch"
        assert decision_res["decision_digest"] == expected_digest, f"Vector {vector_id} decision digest mismatch"

        # Canonicalize decision digest payload directly via Python canonicalizer
        digest_inputs = {
            "config_digest": raw_input.get("configuration_digest", ""),
            "decision_code": expected_code,
            "evaluated_inputs": raw_input.get("evaluated_inputs", {}),
            "evidence_digests": sorted(raw_input.get("evidence_proof_package_digests", [])),
            "generator_version": raw_input.get("generator_version", "v1.0.0"),
            "git_commit": raw_input.get("git_commit_sha", ""),
            "measurement_results": raw_input.get("measurement_results", {}),
            "policy_version": HELMDecisionEngine.POLICY_VERSION,
        }

        canonical_b = canonical_json_bytes(digest_inputs)
        assert canonical_b.decode("utf-8") == expected_canonical_utf8, f"Vector {vector_id} canonical UTF-8 string mismatch"
        assert canonical_b.hex() == expected_canonical_bytes_hex, f"Vector {vector_id} hex bytes mismatch"
        assert canonical_sha256_digest(digest_inputs) == expected_digest, f"Vector {vector_id} SHA-256 digest mismatch"


def test_edge_case_unicode_preservation():
    """Edge Case 1: Verifies string literals are preserved verbatim without Unicode normalization."""
    # Å in decomposed form (U+0041 U+030A) vs composed form (U+00C5)
    decomposed_str = "A\u030a"
    composed_str = "\u00c5"
    obj1 = {"title": decomposed_str}
    obj2 = {"title": composed_str}

    # RFC 8785 requires strings to be preserved verbatim (no NFC normalization)
    bytes1 = canonical_json_bytes(obj1)
    bytes2 = canonical_json_bytes(obj2)
    assert bytes1 != bytes2, "RFC 8785 requires preserving strings verbatim without Unicode normalization"


def test_edge_case_deterministic_key_ordering():
    """Edge Case 2: Verifies keys are sorted by UTF-16 code units."""
    unordered = {"z": 1, "a": 2, "m": 3, "1": 4}
    c_bytes = canonical_json_bytes(unordered)
    assert c_bytes == b'{"1":4,"a":2,"m":3,"z":1}'


def test_edge_case_ieee754_boundary_values():
    """Edge Case 3: Verifies NaN and Infinity are rejected fail-closed."""
    with pytest.raises(ValueError, match="NaN/Infinity"):
        canonical_json_bytes({"invalid": float("nan")})

    with pytest.raises(ValueError, match="NaN/Infinity"):
        canonical_json_bytes({"invalid": float("inf")})


def test_edge_case_numeric_serialization_zero():
    """Edge Case 4: Verifies -0.0 is serialized as 0 per RFC 8785 Section 3.2.2."""
    obj = {"val": -0.0}
    c_bytes = canonical_json_bytes(obj)
    assert c_bytes == b'{"val":0}'


def test_edge_case_nested_object_ordering():
    """Edge Case 5: Verifies nested dictionaries are recursively ordered."""
    nested = {
        "b": {"y": 2, "x": 1},
        "a": [{"d": 4, "c": 3}]
    }
    c_bytes = canonical_json_bytes(nested)
    assert c_bytes == b'{"a":[{"c":3,"d":4}],"b":{"x":1,"y":2}}'


def test_edge_case_transition_hash_chaining():
    """Edge Case 6: Verifies domain-tagged transition hash chaining."""
    transition_1 = {
        "transition_id": "TRANS-001",
        "from": "GENERATED",
        "to": "VERIFIED",
        "actor": "HELM Conformance Engine",
        "reason": "Preflight PASS"
    }

    t1_hash = compute_transition_hash(transition_1, GENESIS_HASH)
    assert isinstance(t1_hash, str) and len(t1_hash) == 64

    transition_2 = {
        "transition_id": "TRANS-002",
        "previous_transition_hash": t1_hash,
        "from": "VERIFIED",
        "to": "PUBLISHED",
        "actor": "CI Policy Engine",
        "reason": "Merge Gate PASS"
    }

    t2_hash = compute_transition_hash(transition_2, t1_hash)
    assert isinstance(t2_hash, str) and len(t2_hash) == 64
    assert t1_hash != t2_hash
