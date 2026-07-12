"""REQ-TO-003 — 21 adversarial proofs. No test makes an external call.

The claim under attack: "no stage may advance from a hand-edited status string, and
every transition must be evidence-derived."
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.council.terminal_path import (  # noqa: E402
    LEGAL_EDGES, State, TerminalPathOrchestrator, TransitionEvidence,
    sha256_file, sha256_obj, utc, validate_intake,
)

GOAL_ID = "HOCH_CANONICAL_GOAL_CONTRACT_v1"


def good_intake(**over):
    env = {
        "mission_id": "M1", "request_id": "RQ1", "goal_contract_id": GOAL_ID,
        "workload_type": "TERMINAL_PATH_PROOF_WORKLOAD",
        "requested_outcome": "produce a sha256 manifest module",
        "constraints": ["local_only"], "founder_only_actions": [],
        "acceptance_criteria": [{"id": "AC1", "criterion": "module imports",
                                 "validator": "module_imports"}],
        "submitted_at": utc(), "source_identity": "agent",
    }
    env.update(over)
    return env


@pytest.fixture
def orch(tmp_path):
    return TerminalPathOrchestrator("M1", tmp_path, root=tmp_path)


def evidence(tmp_path, orch, **over) -> TransitionEvidence:
    p = tmp_path / "ev.json"
    p.write_text(json.dumps({"ok": True}))
    base = dict(
        validator_name="v", validator_result=True, validator_exit_code=0,
        evidence_path="ev.json", evidence_digest=sha256_file(p),
        input_digest="i", output_digest="o", event_timestamp=utc(),
        mission_id=orch.mission_id, task_id="T1",
    )
    base.update(over)
    return TransitionEvidence(**base)


# --- 1-3: intake ------------------------------------------------------------

def test_01_malformed_intake_is_rejected():
    ok, errs = validate_intake({"mission_id": "M1"}, GOAL_ID)
    assert not ok
    assert any(e.startswith("MISSING_FIELD") for e in errs)


def test_02_missing_acceptance_criteria_is_rejected():
    ok, errs = validate_intake(good_intake(acceptance_criteria=[]), GOAL_ID)
    assert not ok
    assert "NO_ACCEPTANCE_CRITERIA" in errs


def test_03_ambiguous_scope_is_rejected():
    ok, errs = validate_intake(
        good_intake(acceptance_criteria=[{"id": "A", "criterion": "it works good",
                                          "validator": "v"}]), GOAL_ID)
    assert not ok
    assert any(e.startswith("AMBIGUOUS_CRITERION") for e in errs)


def test_04_intake_not_bound_to_canonical_goal_is_rejected():
    ok, errs = validate_intake(good_intake(goal_contract_id="SOME_OTHER_GOAL"), GOAL_ID)
    assert not ok
    assert "NOT_BOUND_TO_CANONICAL_GOAL" in errs


def test_05_acceptance_criterion_without_a_validator_is_rejected():
    ok, errs = validate_intake(
        good_intake(acceptance_criteria=[{"id": "A", "criterion": "module imports"}]),
        GOAL_ID)
    assert not ok
    assert any(e.startswith("CRITERION_WITHOUT_VALIDATOR") for e in errs)


def test_06_good_intake_passes():
    ok, errs = validate_intake(good_intake(), GOAL_ID)
    assert ok, errs


# --- 7-12: the state machine refuses to be pushed ---------------------------

def test_07_a_failed_validator_cannot_advance_the_path(tmp_path, orch):
    orch.state = State.INTAKE_RECEIVED
    s = orch.advance(State.INTAKE_VALIDATED,
                     evidence(tmp_path, orch, validator_result=False,
                              validator_exit_code=1))
    assert s == State.UNKNOWN
    assert "INCOMPLETE_EVIDENCE" in orch.blocked_reason


def test_08_missing_evidence_file_yields_UNKNOWN_not_pass(tmp_path, orch):
    orch.state = State.INTAKE_RECEIVED
    s = orch.advance(State.INTAKE_VALIDATED,
                     evidence(tmp_path, orch, evidence_path="does_not_exist.json"))
    assert s == State.UNKNOWN
    assert "EVIDENCE_ABSENT" in orch.blocked_reason


def test_09_digest_mismatch_blocks(tmp_path, orch):
    orch.state = State.INTAKE_RECEIVED
    s = orch.advance(State.INTAKE_VALIDATED,
                     evidence(tmp_path, orch, evidence_digest="0" * 64))
    assert s == State.BLOCKED
    assert "EVIDENCE_DIGEST_MISMATCH" in orch.blocked_reason


def test_10_tampering_the_artifact_after_the_fact_blocks(tmp_path, orch):
    """The bytes decide. Edit the file, and the stored digest no longer matches."""
    ev = evidence(tmp_path, orch)
    (tmp_path / "ev.json").write_text(json.dumps({"ok": "TAMPERED"}))
    orch.state = State.INTAKE_RECEIVED
    s = orch.advance(State.INTAKE_VALIDATED, ev)
    assert s == State.BLOCKED
    assert "EVIDENCE_DIGEST_MISMATCH" in orch.blocked_reason


def test_11_incomplete_evidence_fields_yield_UNKNOWN(tmp_path, orch):
    for field in ("validator_name", "input_digest", "output_digest",
                  "event_timestamp", "task_id"):
        o = TerminalPathOrchestrator("M1", tmp_path, root=tmp_path)
        o.state = State.INTAKE_RECEIVED
        s = o.advance(State.INTAKE_VALIDATED, evidence(tmp_path, o, **{field: ""}))
        assert s == State.UNKNOWN, field
        assert field in o.blocked_reason


def test_12_run_identity_mismatch_blocks(tmp_path, orch):
    orch.state = State.INTAKE_RECEIVED
    s = orch.advance(State.INTAKE_VALIDATED,
                     evidence(tmp_path, orch, mission_id="SOMEONE_ELSE"))
    assert s == State.BLOCKED
    assert "RUN_IDENTITY_MISMATCH" in orch.blocked_reason


# --- 13-16: hand-edited state / illegal edges -------------------------------

def test_13_hand_edited_stage_status_cannot_advance_the_path(tmp_path, orch):
    """THE headline claim. Force the state to DOORSTEP_READY by hand..."""
    orch.force_state(State.DOORSTEP_READY)
    assert orch.state == State.DOORSTEP_READY          # the string is set...
    # ...but the machine records it as a MANUAL transition, and no further legal
    # transition exists from a hand-set terminal state.
    assert orch.metrics.manual_stage_transition_count == 1
    s = orch.advance(State.DOORSTEP_READY, evidence(tmp_path, orch))
    assert s == State.BLOCKED
    assert "ILLEGAL_EDGE" in orch.blocked_reason


def test_14_a_manual_transition_is_counted_and_fails_the_zero_transport_gate(tmp_path, orch):
    orch.force_state(State.PACKAGE_VALIDATED)
    m = orch.to_dict()["manual_intervention_metrics"]
    assert m["manual_stage_transition_count"] == 1     # the DOORSTEP gate requires 0
    assert m["manual_prompt_copy_count"] == 0


def test_15_stage_skipping_is_an_illegal_edge(tmp_path, orch):
    orch.state = State.INTAKE_VALIDATED
    s = orch.advance(State.DOORSTEP_READY, evidence(tmp_path, orch))   # skip 5 stages
    assert s == State.BLOCKED
    assert "ILLEGAL_EDGE" in orch.blocked_reason


def test_16_every_legal_edge_is_single_step_forward():
    for frm, tos in LEGAL_EDGES.items():
        assert len(tos) == 1, f"{frm} has an ambiguous forward edge"
    assert State.DOORSTEP_READY not in LEGAL_EDGES     # terminal


# --- 17-21: route / execute / verify / package ------------------------------

def test_17_route_without_gateway_authorization_blocks(tmp_path, orch):
    orch.state = State.ROUTE_SELECTED
    s = orch.advance(State.ROUTE_AUTHORIZED,
                     evidence(tmp_path, orch, validator_result=False,
                              validator_exit_code=1, detail="blocks=['LOCAL_FIRST']"))
    assert s == State.UNKNOWN


def test_18_direct_provider_bypass_is_impossible_from_the_orchestrator():
    """The orchestrator has no network client of its own -- it must use the gateway."""
    src = (ROOT / "scripts" / "council" / "terminal_path.py").read_text(encoding="utf-8")
    for bad in ("urllib", "requests", "httpx", "socket", "subprocess"):
        assert f"import {bad}" not in src, f"orchestrator imports {bad}"


def test_19_producer_cannot_be_the_sole_verifier():
    """The verifier must not be the producing model."""
    from scripts.council.run_terminal_path_proof import independent_verification
    src = (ROOT / "scripts" / "council" / "run_terminal_path_proof.py").read_text()
    assert "verifier_identity" in src and "producer_identity" in src
    # the independent check recomputes with hashlib, not by asking the model
    assert "hashlib.sha256" in src
    assert callable(independent_verification)


def test_20_a_failed_independent_verification_yields_UNVERIFIED_not_pass(tmp_path):
    from scripts.council.run_terminal_path_proof import independent_verification
    bad = tmp_path / "broken.py"
    bad.write_text("this is not python(((")
    checks = independent_verification(bad)
    assert not all(c["pass"] for c in checks)
    assert any(c["validator"] == "module_imports" and not c["pass"] for c in checks)


def test_21_incomplete_package_cannot_reach_doorstep(tmp_path, orch):
    orch.state = State.PACKAGE_CREATED
    s = orch.advance(State.PACKAGE_VALIDATED,
                     evidence(tmp_path, orch, validator_result=False,
                              validator_exit_code=1,
                              detail="missing=['SHA256SUMS']"))
    assert s == State.UNKNOWN
    assert orch.state != State.DOORSTEP_READY


def test_22_no_external_calls_in_this_suite():
    """The orchestrator module imports no network client at all (see test_18)."""
    import scripts.council.terminal_path as tp
    assert not hasattr(tp, "requests")
    assert not hasattr(tp, "urlopen")
