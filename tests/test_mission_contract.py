"""Tests for the HELM Mission Contract v1 (EDR-0007).

Run: python3 -m pytest tests/test_mission_contract.py -q
 or: python3 tests/test_mission_contract.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from backend.helm_runtime import mission_contract as mc
from backend.security import proof_contract as pc


def base_mission(**over):
    m = {
        "MISSION_ID": "M-HFF-RECURRING-DEPLOY-001",
        "TITLE": "Take Recurring Charge Finder to live checkout",
        "OWNER": "founder",
        "ROLE": "builder",
        "OBJECTIVE": "A stranger can reach a working $9 checkout.",
        "SUCCESS_CRITERIA": ["checkout endpoint returns a real Stripe URL"],
        "INPUTS": ["products/hff-recurring-charges/README.md"],
        "EXPECTED_OUTPUTS": ["docs/evidence/runtime/verify.md"],
        "SCOPE": ["products/hff-recurring-charges/"],
        "TOOLS_ALLOWED": ["bash", "git"],
        "CONSTRAINTS": ["no secrets written to the repo"],
        "EDR_REQUIRED": "NO",
        "FOUNDER_GATES": ["KEYS", "SPEND"],
        "STOP_CONDITIONS": ["founder gate encountered", "missing evidence"],
        "EVIDENCE_REQUIRED": ["logs", "tests"],
        "TRUTH_SOURCE": "LIVE_RUNTIME",
        "RETURN": "DONE | PARTIAL | BLOCKED + evidence paths",
    }
    m.update(over)
    return m


# --- binding to the ratified truth enum -------------------------------------

def test_binds_the_ratified_truth_enum_rather_than_forking_it():
    assert mc.Truth is pc.Truth
    assert mc.ADVANCING == pc.ADVANCING


def test_every_truth_source_projects_onto_a_ratified_class():
    for src, truth in mc.TRUTH_SOURCE_PROJECTION.items():
        assert isinstance(truth, pc.Truth), f"{src} must project onto the ratified enum"


def test_runtime_and_tests_advance_state():
    assert mc.advances_state("LIVE_RUNTIME")
    assert mc.advances_state("TEST_EXECUTION")
    assert mc.advances_state("DETERMINISTIC_SCRIPT")


def test_static_analysis_does_not_advance_state():
    """A clean linter reads source; it is not evidence the system behaved."""
    assert mc.projected_truth("STATIC_ANALYSIS") is pc.Truth.ASSERTED
    assert not mc.advances_state("STATIC_ANALYSIS")


def test_human_input_does_not_advance_state():
    """Founder authority governs gates, not evidence."""
    assert mc.projected_truth("HUMAN_INPUT") is pc.Truth.ASSERTED
    assert not mc.advances_state("HUMAN_INPUT")


def test_unknown_mechanism_is_rejected():
    with pytest.raises(mc.MissionContractError):
        mc.projected_truth("VIBES")


# --- validation happy path ---------------------------------------------------

def test_valid_mission_validates_and_exposes_its_truth_class():
    m = mc.validate(base_mission())
    assert m.mission_id == "M-HFF-RECURRING-DEPLOY-001"
    assert m.truth is pc.Truth.OBSERVED
    assert m.advancing is True
    ok, _ = m.may_return_done()
    assert ok


# --- fail closed -------------------------------------------------------------

def test_missing_required_field_fails_closed():
    bad = base_mission()
    del bad["TRUTH_SOURCE"]
    with pytest.raises(mc.MissionContractError) as e:
        mc.validate(bad)
    assert any("TRUTH_SOURCE" in x for x in e.value.violations)


def test_all_violations_are_reported_at_once():
    bad = base_mission(ROLE="wizard", OWNER="intern", TRUTH_SOURCE="VIBES")
    with pytest.raises(mc.MissionContractError) as e:
        mc.validate(bad)
    assert len(e.value.violations) >= 3


def test_non_dict_mission_fails_closed():
    with pytest.raises(mc.MissionContractError):
        mc.validate("MISSION_ID: nope")  # type: ignore[arg-type]


# --- invariants --------------------------------------------------------------

def test_declaring_a_founder_gate_requires_a_stop_condition():
    bad = base_mission(STOP_CONDITIONS=["missing evidence"])
    with pytest.raises(mc.MissionContractError) as e:
        mc.validate(bad)
    assert any("never authorizes it" in x for x in e.value.violations)


def test_a_mission_with_no_founder_gates_is_allowed_to_have_none():
    ok = mc.validate(base_mission(FOUNDER_GATES=[], STOP_CONDITIONS=["missing evidence"]))
    assert ok.founder_gates == []


def test_unknown_founder_gate_is_rejected():
    with pytest.raises(mc.MissionContractError) as e:
        mc.validate(base_mission(FOUNDER_GATES=["VIBES"]))
    assert any("unknown gate" in x for x in e.value.violations)


def test_edr_required_yes_obliges_an_edr_output():
    with pytest.raises(mc.MissionContractError) as e:
        mc.validate(base_mission(EDR_REQUIRED="YES"))
    assert any("EDR" in x for x in e.value.violations)
    mc.validate(base_mission(EDR_REQUIRED="YES",
                             EXPECTED_OUTPUTS=["docs/helm/edr/EDR-0008-thing.md"]))


def test_empty_allowlist_is_an_error_not_a_wildcard():
    for f in ("SCOPE", "TOOLS_ALLOWED"):
        with pytest.raises(mc.MissionContractError) as e:
            mc.validate(base_mission(**{f: []}))
        assert any("never a wildcard" in x for x in e.value.violations)


def test_return_must_reference_a_sanctioned_value():
    with pytest.raises(mc.MissionContractError):
        mc.validate(base_mission(RETURN="basically finished"))


# --- NO FAKE GREEN -----------------------------------------------------------

def test_done_is_refused_on_a_non_advancing_truth_source():
    for src in ("STATIC_ANALYSIS", "HUMAN_INPUT", "UNKNOWN"):
        m = mc.validate(base_mission(TRUTH_SOURCE=src))
        ok, why = m.may_return_done()
        assert not ok, f"{src} must not support a DONE claim"
        assert "ADVANCING" in why


# --- allowlist semantics -----------------------------------------------------

def test_scope_is_an_allowlist_of_path_prefixes():
    m = mc.validate(base_mission())
    assert m.permits_path("products/hff-recurring-charges/engine/index.js")
    assert not m.permits_path("backend/helm_runtime/transaction.py")
    assert not m.permits_path("products/hff-invoice-aging/engine/index.js")


def test_scope_prefix_matching_does_not_leak_to_sibling_directories():
    m = mc.validate(base_mission(SCOPE=["products/hff-recurring"]))
    assert not m.permits_path("products/hff-recurring-charges/engine/index.js")


def test_tools_are_an_allowlist():
    m = mc.validate(base_mission())
    assert m.permits_tool("bash")
    assert not m.permits_tool("vercel")


# --- conformance survey (non-raising) ---------------------------------------

def test_conformance_reports_without_raising():
    r = mc.conformance({"mission_id": "M-HASF-REAL-01", "factory": "HASF"})
    assert r["conforms"] is False
    assert r["required_missing"]
    assert mc.conformance(base_mission())["conforms"] is True


def test_schema_file_matches_the_code():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    schema = mc.load_schema(root)
    assert schema["schema"] == mc.SCHEMA_NAME
    assert set(schema["required_fields"]) == set(mc.REQUIRED_FIELDS)
    assert set(schema["enums"]["TRUTH_SOURCE"]) == set(mc.TRUTH_SOURCE_PROJECTION)
    assert set(schema["enums"]["FOUNDER_GATES"]) == set(mc.FOUNDER_GATES)
    for src, cls in schema["truth_source_projection"].items():
        if src == "note":
            continue
        assert mc.TRUTH_SOURCE_PROJECTION[src].value == cls


# --- EXECUTION_CONTEXT (EDR-0007 amendment 1) --------------------------------

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def test_execution_context_reuses_correlation_id_not_a_new_run_id():
    """The incumbent identifier is correlation_id (transaction.py). Do not fork it."""
    assert "correlation_id" in mc.EXECUTION_CONTEXT_FIELDS
    assert "run_id" not in mc.EXECUTION_CONTEXT_FIELDS


def test_capture_returns_every_declared_field():
    ctx = mc.capture_execution_context(ROOT)
    for f in mc.EXECUTION_CONTEXT_FIELDS:
        assert f in ctx, f"capture must return {f}"


def test_capture_pins_a_real_commit_sha_in_a_git_repo():
    ctx = mc.capture_execution_context(ROOT)
    sha = ctx["commit_sha"]
    assert sha == mc.UNKNOWN_VALUE or len(sha) == 40, "a sha is 40 hex chars or UNKNOWN"


def test_capture_never_invents_a_value_outside_a_repo(tmp_path):
    """Outside git, commit_sha must be UNKNOWN — not guessed, not defaulted."""
    ctx = mc.capture_execution_context(str(tmp_path))
    assert ctx["commit_sha"] == mc.UNKNOWN_VALUE
    assert ctx["mission_schema_version"] == mc.UNKNOWN_VALUE
    assert ctx["doctrine_version"] == mc.UNKNOWN_VALUE


def test_supplied_correlation_id_is_preserved():
    ctx = mc.capture_execution_context(ROOT, correlation_id="corr-123")
    assert ctx["correlation_id"] == "corr-123"


def test_reproducibility_flags_a_dirty_tree():
    ctx = {"correlation_id": "c", "commit_sha": "a" * 40, "dirty": True,
           "runtime_version": "r", "doctrine_version": "d", "mission_schema_version": "s"}
    r = mc.reproducibility(ctx)
    assert r["reproducible"] is False
    assert any("uncommitted" in x for x in r["reasons"])


def test_reproducibility_flags_an_unknown_commit():
    ctx = {"correlation_id": "c", "commit_sha": mc.UNKNOWN_VALUE, "dirty": False,
           "runtime_version": "r", "doctrine_version": "d", "mission_schema_version": "s"}
    assert mc.reproducibility(ctx)["reproducible"] is False


def test_clean_pinned_context_is_reproducible():
    ctx = {"correlation_id": "c", "commit_sha": "b" * 40, "dirty": False,
           "runtime_version": "r", "doctrine_version": "d", "mission_schema_version": "s"}
    r = mc.reproducibility(ctx)
    assert r["reproducible"] is True
    assert r["reasons"] == []


def test_reproducibility_reports_but_does_not_block():
    """A dirty tree must not raise — governance that halts all work is theatre."""
    ctx = mc.capture_execution_context(ROOT)
    assert isinstance(mc.reproducibility(ctx)["reproducible"], bool)


def test_execution_context_validation_fails_closed_on_missing_field():
    ctx = mc.capture_execution_context(ROOT)
    del ctx["commit_sha"]
    with pytest.raises(mc.MissionContractError):
        mc.validate_execution_context(ctx)


def test_execution_context_rejects_a_forked_run_id():
    ctx = mc.capture_execution_context(ROOT)
    ctx["run_id"] = "CERT-6H-something"
    with pytest.raises(mc.MissionContractError) as e:
        mc.validate_execution_context(ctx)
    assert any("fork" in x for x in e.value.violations)


def test_execution_context_validates_when_complete():
    assert mc.validate_execution_context(mc.capture_execution_context(ROOT))


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
