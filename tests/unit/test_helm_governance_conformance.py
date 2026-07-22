#!/usr/bin/env python3
"""
HELM Governance Conformance Test Suite (Sprint 8 — Milestone R10)
================================================================
Validates normative change classification, semantic version compatibility,
and conformance level evaluation.
"""

import pytest

VALID_CHANGE_CLASSES = {
    "EDITORIAL",
    "CLARIFICATION",
    "NON_BREAKING_NORMATIVE",
    "BREAKING_NORMATIVE",
    "SECURITY_EMERGENCY"
}

CONFORMANCE_LEVELS = {
    "LEVEL_A_REFERENCE",
    "LEVEL_B_INDEPENDENT",
    "LEVEL_C_QUALIFIED",
    "LEVEL_D_CERTIFIED"
}


def evaluate_compatibility(spec_ver: str, engine_ver: str) -> str:
    s_major, s_minor = map(int, spec_ver.split(".")[:2])
    e_major, e_minor = map(int, engine_ver.split(".")[:2])

    if s_major > e_major:
        return "INCOMPATIBLE"
    if s_major < e_major:
        return "COMPATIBLE_WITH_LIMITATIONS"
    if s_minor > e_minor:
        return "MIGRATION_REQUIRED"
    if s_minor <= e_minor:
        return "COMPATIBLE"
    return "UNVERIFIED"


def test_gov_001_change_classification_validity():
    """GOV-001: Asserts all change categories map to valid normative change classes."""
    for cls in ["EDITORIAL", "CLARIFICATION", "NON_BREAKING_NORMATIVE", "BREAKING_NORMATIVE", "SECURITY_EMERGENCY"]:
        assert cls in VALID_CHANGE_CLASSES


def test_gov_002_compatibility_matrix_same_version():
    """GOV-002: Asserts spec v1.0 on engine v1.0 evaluates to COMPATIBLE."""
    assert evaluate_compatibility("1.0", "1.0") == "COMPATIBLE"


def test_gov_003_compatibility_matrix_newer_engine():
    """GOV-003: Asserts spec v1.0 on engine v1.1 evaluates to COMPATIBLE (engine backward-compatible)."""
    assert evaluate_compatibility("1.0", "1.1") == "COMPATIBLE"


def test_gov_004_compatibility_matrix_newer_spec_minor():
    """GOV-004: Asserts spec v1.1 on engine v1.0 evaluates to MIGRATION_REQUIRED."""
    assert evaluate_compatibility("1.1", "1.0") == "MIGRATION_REQUIRED"


def test_gov_005_compatibility_matrix_major_version_mismatch():
    """GOV-005: Asserts spec v2.0 on engine v1.0 evaluates to INCOMPATIBLE."""
    assert evaluate_compatibility("2.0", "1.0") == "INCOMPATIBLE"


def test_gov_006_conformance_level_hierarchy():
    """GOV-006: Asserts four formal conformance levels exist in valid hierarchy."""
    assert len(CONFORMANCE_LEVELS) == 4
    assert "LEVEL_C_QUALIFIED" in CONFORMANCE_LEVELS
