"""test_engineering_doctrine.py — executable proof of HELM Engineering Doctrine v1.0.

HELM-GOV | extends: test suite | doctrine: Governance-before-Capability | edr: EDR-0006 (AC-1, AC-2)
         | why: proves the single gate is fail-closed (six negative controls, one per Proof Record
         | property), that legacy is never auto-promoted, and that exactly one governance gate exists.

This is the REQ-GOV-007 validator. Every negative control demonstrates the gate REJECTS a broken
state — NEGATIVE-CONTROL-001 applied to governance itself.
"""
from __future__ import annotations

import copy

import pytest

from backend.helm_runtime import governance_manifest as gm
from backend.helm_runtime.extensions.constitutional_gate import govern_decision


def _complete_record() -> dict:
    """A complete, advancing Proof Record — the known-GOOD state (positive control)."""
    return {
        "authorized": {"authority": "EDR-0006", "decision_id": "D1", "gate": "govern_decision"},
        "explanation": "route mission to builder lane",
        "trace": {"correlation_id": "c1", "input_digests": ["sha256:abc"]},
        "proven": {"proof_command": "pytest -q", "exit_code": 0, "evidence_hash": "sha256:def"},
        "audit": {"record_hash": "h1", "prev_hash": None},
        "reproducibility": {"tested_commit": "12b21e60", "environment": "py3"},
        "evidence_class": "OBSERVED",
    }


# ── POSITIVE CONTROL — a complete record advances ─────────────────────────────────────────────
def test_positive_control_complete_record_is_governed():
    r = govern_decision(_complete_record())
    assert r.governance_state == gm.GOVERNED
    assert r.may_advance is True


# ── SIX NEGATIVE CONTROLS — removing ANY property blocks advancement (AC-1) ────────────────────
@pytest.mark.parametrize("prop", ["authorized", "explanation", "trace", "proven", "audit", "reproducibility"])
def test_negative_control_missing_property_blocks(prop):
    """One negative control per doctrine property: Authorized/Explained/Traced/Proven/Audited/Reproduced."""
    rec = _complete_record()
    del rec[prop]
    r = govern_decision(rec)
    assert r.may_advance is False, f"gate must fail-closed when '{prop}' is missing"
    assert r.governance_state == gm.UNKNOWN
    assert prop in " ".join(r.missing)


def test_negative_control_empty_subfield_blocks():
    """A present-but-empty required sub-field is still incomplete (no hollow governance)."""
    rec = _complete_record()
    rec["proven"]["evidence_hash"] = ""
    r = govern_decision(rec)
    assert r.may_advance is False
    assert "proven.evidence_hash" in r.missing


# ── ANTI-THEATER — self-asserted evidence never advances (INV-5) ───────────────────────────────
@pytest.mark.parametrize("cls", ["ASSERTED", "CACHED", "UNKNOWN"])
def test_non_advancing_evidence_class_blocks(cls):
    rec = _complete_record()
    rec["evidence_class"] = cls
    r = govern_decision(rec)
    assert r.may_advance is False, f"{cls} evidence must not advance state"


# ── FAIL-CLOSED — no record at all ─────────────────────────────────────────────────────────────
def test_missing_record_fails_closed():
    assert govern_decision(None).may_advance is False
    assert govern_decision(gm.blank_proof_record()).governance_state == gm.UNKNOWN


# ── LEGACY IS NEVER AUTO-PROMOTED (INV-3 / AC-3) ───────────────────────────────────────────────
def test_legacy_complete_is_verified_not_governed():
    """A complete legacy record classifies VERIFIED — never GOVERNED without a migration record."""
    state, _ = gm.classify_legacy(_complete_record())
    assert state == gm.LEGACY_VERIFIED
    assert state != gm.GOVERNED


def test_legacy_sourced_record_cannot_be_governed_without_migration():
    """AC-3/INV-3 enforced at the GATE: a COMPLETE, advancing, but LEGACY-sourced record is blocked
    from GOVERNED unless it carries a migration record — even via govern_decision(legacy=False)."""
    rec = _complete_record()
    rec["source"] = gm.SOURCE_LEGACY
    r = govern_decision(rec)  # legacy=False on purpose — the mis-flag path the Auditor flagged
    assert r.governance_state == gm.NEEDS_MIGRATION and r.may_advance is False
    # add a proper migration record -> now promotable
    rec["migration"] = {"migration_ref": "MIG-001", "migrated_by": "builder"}
    assert govern_decision(rec).governance_state == gm.GOVERNED


def test_legacy_partial_needs_migration_empty_unknown():
    partial = {"trace": {"correlation_id": "c"}, "audit": {"record_hash": "h"}, "evidence_class": "CACHED"}
    assert gm.classify_legacy(partial)[0] == gm.LEGACY_NEEDS_MIGRATION
    assert gm.classify_legacy({})[0] == gm.LEGACY_UNKNOWN


# ── SINGLE AUTHORITATIVE GATE (AC-2 / Founder Directive #1) ─────────────────────────────────────
def test_exactly_one_governance_gate_exists():
    """Structural proof that governance classification lives in ONE place. Any second
    'def govern_decision' or a re-implementation of GOVERNED/NEEDS_MIGRATION classification in
    another module is a duplication violation."""
    import subprocess

    from backend.helm_runtime import governance_engine

    root = __import__("pathlib").Path(governance_engine.__file__).resolve().parents[2]
    out = subprocess.run(
        ["git", "grep", "--untracked", "-l", "-E", "^def govern_decision", "--", "*.py"],
        cwd=str(root), capture_output=True, text=True,
    ).stdout.strip().splitlines()
    # A7 remediation 2026-07-19: the ONE gate now lives in the composed extension module
    # (frozen governance_engine.py is byte-restored to d8d5139a and defines no gate).
    defining = [p for p in out if p.endswith("extensions/constitutional_gate.py")]
    in_frozen = [p for p in out if p.endswith("helm_runtime/governance_engine.py")]
    assert len(defining) == 1 and not in_frozen, f"expected one gate definition (extension only), found: {out}"
    others = [p for p in out if not p.endswith("extensions/constitutional_gate.py")]
    assert others == [], f"parallel governance gate(s) found: {others}"


# ── DELEGATION — the Evidence Resolver defers to the one gate (R3) ─────────────────────────────
def test_evidence_resolver_delegates_to_gate():
    import time

    from backend.security.proof_contract import Evidence, ProofContract, Truth, may_advance_state

    ev = Evidence(
        classification=Truth.OBSERVED, observed_at=time.time(), proof_command="p", exit_code=0,
        raw_evidence_sha256="r", tested_commit="c", positive_control_passed=True, negative_control_passed=True,
    )
    contract = ProofContract.validate({
        "goal": "g", "mechanism": "m", "proof_command": "p", "expected_result": "r",
        "constraints": ["x"], "failure_behavior": "BLOCKED",
    })
    # good evidence + bad governance record -> blocked BY governance, proving delegation
    ok, msg = may_advance_state(ev, contract, proof_record={"evidence_class": "ASSERTED"})
    assert ok is False and "governance" in msg.lower()
    # good evidence + no governance record -> unchanged legacy behavior (backward compat)
    ok2, _ = may_advance_state(ev, contract)
    assert ok2 is True


# ── CONTINUOUS PROOF — N8 ConMon re-derives coverage from the event bus (R7 / AC-4) ────────────
def test_conmon_governance_coverage_counts_new_governed_decisions(tmp_path, monkeypatch):
    """End-to-end: a NEW governed council event is picked up by ConMon; a legacy (pre-adoption)
    event is excluded, not counted as a failure."""
    from backend.helm_runtime.event_bus import publish_event
    from backend.security import helm_conmon

    ledger = tmp_path / "helm_events.jsonl"
    monkeypatch.setattr(helm_conmon, "EVENTS_LEDGER", ledger)
    monkeypatch.setattr(helm_conmon, "_adoption_cutoff", lambda: "2026-07-18T00:00:00Z")

    # a legacy pre-adoption council event with no Proof Record -> excluded
    publish_event(type="COUNCIL_SOLVED", producer="council_router", mission_id="COUNCIL",
                  payload={"timestamp_note": "legacy"}, path=ledger)
    # NOTE publish_event stamps the current timestamp; to simulate legacy we append one by hand:
    legacy = '{"producer":"council_router","type":"COUNCIL_SOLVED","timestamp":"2026-07-01T00:00:00Z","proof_record":null}\n'
    with open(ledger, "a") as fh:
        fh.write(legacy)

    # a NEW governed decision (post-adoption timestamp from publish_event) carrying a GOVERNED record
    rec = _complete_record()
    rec["governance_state"] = "GOVERNED"
    from backend.helm_runtime.extensions.constitutional_gate import publish_governed_event as _pge
    _pge(type="COUNCIL_SOLVED", producer="council_router", mission_id="COUNCIL",
         proof_record=rec, path=ledger)

    cov = helm_conmon.governance_coverage()
    assert cov["legacy_excluded"] >= 1, "pre-adoption event must be excluded"
    assert cov["carrying_proof_record"] >= 1 and cov["governed"] >= 1
    assert cov["governed_rate"] == 1.0
