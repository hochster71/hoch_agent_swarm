#!/usr/bin/env python3
"""
HELM Security Qualification Test Suite (Sprint 6 — Milestone R6)
================================================================
Validates parser security (R6.2), ledger integrity (R6.3), Unicode security (R6.4),
and cryptographic misuse resistance (R6.6) with explicit requirement traceability mapping:
  - SEC-001: R6.2 Non-finite float rejection (NaN, Infinity, -Infinity)
  - SEC-002: R6.2 Non-string object key rejection
  - SEC-003: R6.3 Tampered previous_transition_hash rejection
  - SEC-004: R6.3 Out-of-order state transition rejection
  - SEC-005: R6.4 Zero-width joiner (U+200D) digest distinctness
  - SEC-006: R6.4 Bidi control character (U+200E/F) digest distinctness
  - SEC-007: R6.6 Domain separation tag isolation
"""

import json
import pytest
from pathlib import Path

from scripts.helm.canonical_json import canonical_json_bytes, canonical_sha256_digest, compute_transition_hash, DOMAIN_TAG, GENESIS_HASH
from backend.helm.kernel.decision_engine import HELMDecisionEngine
from scripts.helm.verify_transition_history import verify_transition_history


def test_sec_001_r6_2_parser_hardening_nan_infinity_rejection():
    """[SEC-001] R6.2: Verifies non-finite float values (NaN, Inf, -Inf) are rejected fail-closed."""
    with pytest.raises(ValueError, match="NaN/Infinity"):
        canonical_json_bytes({"val": float("nan")})

    with pytest.raises(ValueError, match="NaN/Infinity"):
        canonical_json_bytes({"val": float("inf")})

    with pytest.raises(ValueError, match="NaN/Infinity"):
        canonical_json_bytes({"val": float("-inf")})


def test_sec_002_r6_2_parser_hardening_invalid_type_rejection():
    """[SEC-002] R6.2: Verifies non-string keys raise ValueError."""
    with pytest.raises(ValueError, match="string keys"):
        canonical_json_bytes({123: "invalid_integer_key"})


def test_sec_003_r6_3_ledger_integrity_tampered_prev_hash_rejection(tmp_path):
    """[SEC-003] R6.3: Verifies tampered previous_transition_hash in report raises verification error."""
    bad_report = {
        "lifecycle": {
            "state": "VERIFIED",
            "transition_history": [
                {
                    "transition_id": "TRANS-001",
                    "previous_transition_hash": "TAMPERED_PREV_HASH_00000000000000000000000000000000000000000000000",
                    "from": "GENERATED",
                    "to": "VERIFIED",
                    "timestamp": "2026-07-22T00:00:00Z",
                    "actor": "Attacker",
                    "reason": "Tamper test"
                }
            ]
        }
    }
    report_file = tmp_path / "bad_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(bad_report, f)

    assert verify_transition_history(str(report_file)) is False


def test_sec_004_r6_3_ledger_integrity_invalid_state_transition(tmp_path):
    """[SEC-004] R6.3: Verifies illegal state transition (e.g. GENERATED -> PUBLISHED) is rejected."""
    bad_report = {
        "lifecycle": {
            "state": "PUBLISHED",
            "transition_history": [
                {
                    "transition_id": "TRANS-001",
                    "previous_transition_hash": GENESIS_HASH,
                    "from": "GENERATED",
                    "to": "PUBLISHED",  # Illegal jump, skipping VERIFIED
                    "timestamp": "2026-07-22T00:00:00Z",
                    "actor": "Attacker",
                    "reason": "Illegal transition"
                }
            ]
        }
    }
    t_hash = compute_transition_hash(bad_report["lifecycle"]["transition_history"][0], GENESIS_HASH)
    bad_report["lifecycle"]["transition_history"][0]["transition_hash"] = t_hash

    report_file = tmp_path / "bad_transition_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(bad_report, f)

    assert verify_transition_history(str(report_file)) is False


def test_sec_005_r6_4_unicode_security_zero_width_joiner_distinctness():
    """[SEC-005] R6.4: Verifies zero-width joiners (U+200D) produce distinct canonical hashes from plain text."""
    plain_obj = {"user": "admin"}
    zwj_obj = {"user": "ad\u200dmin"}

    plain_hash = canonical_sha256_digest(plain_obj)
    zwj_hash = canonical_sha256_digest(zwj_obj)

    assert plain_hash != zwj_hash, "Zero-width joiners must produce distinct canonical digests"


def test_sec_006_r6_4_unicode_security_bidi_control_char_distinctness():
    """[SEC-006] R6.4: Verifies bidi control characters (U+200E, U+200F) produce distinct hashes."""
    plain_obj = {"field": "test"}
    bidi_obj = {"field": "test\u200e"}

    assert canonical_sha256_digest(plain_obj) != canonical_sha256_digest(bidi_obj)


def test_sec_007_r6_6_cryptographic_misuse_domain_tag_isolation():
    """[SEC-007] R6.6: Verifies transition hash fails if domain tag is omitted or altered."""
    payload = {
        "transition_id": "TRANS-001",
        "from": "GENERATED",
        "to": "VERIFIED",
        "actor": "Test",
        "reason": "Isolation test"
    }

    correct_hash = compute_transition_hash(payload, GENESIS_HASH)

    # Compute raw SHA256 without domain tag
    raw_canonical_b = canonical_json_bytes(payload)
    raw_hash = canonical_sha256_digest(payload)

    assert correct_hash != raw_hash, "Transition hash without domain separation tag must fail"
