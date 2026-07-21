"""HRF-RUNTIME-001 regression tests.

The property under test is NOT "the happy path works". It is that the runtime CANNOT
report success it did not observe. Every test below tries to obtain OPERATIONAL_PROVEN
without earning it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.helm_runtime.hrf_runtime import (  # noqa: E402
    BudgetLedger, Outcome, SandboxViolation, fact_check_verifier, load_factory,
    enforce_sandbox, run, validate_intake,
)

GOOD = {"query": "what is the provenance contract"}


def _fake(responses):
    """Deterministic dispatch stub. Keeps the runtime testable without a live model —
    a capability proof that depends on model availability proves availability, not the path."""
    calls = {"n": 0}

    def _d(lane, prompt, **kw):
        i = calls["n"]
        calls["n"] += 1
        return responses[i] if i < len(responses) else {"ok": False, "status": "EXHAUSTED"}

    return _d


def _ok(text, cost=0.0):
    return {"ok": True, "text": text, "cost": cost, "model": "stub"}


# --- the runtime must not manufacture success --------------------------------

def test_no_public_way_to_assert_an_outcome():
    """State is DERIVED. If a setter existed, every other guarantee would be advisory."""
    import backend.helm_runtime.hrf_runtime as m
    assert not hasattr(m, "set_outcome")
    assert not any(n.startswith("set_") for n in dir(m))


def test_all_roles_execute_and_verifier_passes_yields_OPERATIONAL_PROVEN():
    d = _fake([_ok("1. claim A SOURCE: doi:x"),
               _ok("1. claim A SUPPORTED"),
               _ok("Brief: claim A holds.")])
    r = run(GOOD, dispatch=d)
    assert r["outcome"] == Outcome.OPERATIONAL_PROVEN.value
    assert r["verifier"]["passed"] is True
    assert set(r["components_executed"]) >= {"Researcher", "Evidence Auditor",
                                             "Synthesis Writer", "fact_check_verifier"}


def test_a_failed_role_is_PARTIAL_never_PROVEN():
    d = _fake([_ok("1. claim A"), {"ok": False, "status": "GATEWAY_ERROR", "message": "down"}])
    r = run(GOOD, dispatch=d)
    assert r["outcome"] == Outcome.PARTIAL.value
    assert r["outcome"] != Outcome.OPERATIONAL_PROVEN.value


def test_verifier_failure_blocks_PROVEN_even_when_every_role_ran():
    """All three roles succeeded; the validator did not. Success of the parts is not
    success of the whole."""
    d = _fake([_ok("1. claim A SOURCE: NONE"),
               _ok("1. claim A UNSUPPORTED — no source"),
               _ok("Brief: claim A SOURCE: NONE")])
    r = run(GOOD, dispatch=d)
    assert r["verifier"]["passed"] is False
    assert r["outcome"] == Outcome.PARTIAL.value


def test_nothing_executed_is_NOT_OPERATIONAL_not_UNKNOWN():
    d = _fake([{"ok": False, "status": "GATEWAY_ERROR", "message": "no model"}])
    r = run(GOOD, dispatch=d)
    assert r["outcome"] in (Outcome.PARTIAL.value, Outcome.NOT_OPERATIONAL.value)
    assert r["steps"][0]["ok"] is False


# --- fail-closed controls -----------------------------------------------------

def test_intake_missing_required_field_HALTS_as_BLOCKED():
    r = run({"sources": ["a"]}, dispatch=_fake([_ok("x")]))
    assert r["outcome"] == Outcome.BLOCKED.value
    assert "query" in r["halted_reason"]


def test_intake_rejects_wrong_types():
    with pytest.raises(SandboxViolation):
        validate_intake({"query": 123}, {"required": ["query"],
                                         "properties": {"query": {"type": "string"}}})


@pytest.mark.parametrize("env,scope", [("cloud", "read-only"), ("local_only", "write")])
def test_SANDBOX_STRICT_refuses_non_local_or_writable(env, scope):
    with pytest.raises(SandboxViolation):
        enforce_sandbox("SANDBOX_STRICT", environment=env, scope=scope)


def test_unknown_security_policy_refuses_rather_than_defaults():
    """An unrecognised policy must not silently fall through to permissive behaviour."""
    with pytest.raises(SandboxViolation):
        enforce_sandbox("SANDBOX_LOOSE", environment="local_only", scope="read-only")


def test_budget_refuses_BEFORE_dispatch():
    b = BudgetLedger(per_task_limit_usd=0.5, monthly_limit_usd=100.0)
    with pytest.raises(SandboxViolation):
        b.authorize(0.51)


def test_monthly_budget_accumulates_and_then_refuses():
    b = BudgetLedger(per_task_limit_usd=10.0, monthly_limit_usd=10.0)
    b.authorize(6.0); b.record(6.0)
    with pytest.raises(SandboxViolation):
        b.authorize(5.0)


def test_undeclared_role_halts_rather_than_being_skipped():
    """A role in the registry with no implementation must BLOCK. Skipping it would let the
    run report success for a component that never existed — GOV-017 exactly."""
    import backend.helm_runtime.hrf_runtime as m
    fac = load_factory("HRF")
    original = dict(m.ROLE_PROMPTS)
    try:
        m.ROLE_PROMPTS.pop(fac["agent_roles"][0])
        r = run(GOOD, dispatch=_fake([_ok("x")]))
        assert r["outcome"] == Outcome.BLOCKED.value
        assert "not implemented" in r["halted_reason"]
    finally:
        m.ROLE_PROMPTS.clear(); m.ROLE_PROMPTS.update(original)


# --- validator behaviour ------------------------------------------------------

def test_verifier_is_offline_and_deterministic():
    """Same inputs, same verdict — and no dispatch involved. A validator that called the
    model it validates would supply no independent signal (ARCH-001)."""
    a = fact_check_verifier("Brief text", "1. claim SUPPORTED")
    b = fact_check_verifier("Brief text", "1. claim SUPPORTED")
    assert a == b and a["passed"] is True


def test_verifier_catches_unsourced_claim_in_brief():
    v = fact_check_verifier("Finding X SOURCE: NONE", "1. X SUPPORTED")
    assert v["passed"] is False


def test_empty_brief_fails_verification():
    assert fact_check_verifier("", "1. X SUPPORTED")["passed"] is False


# --- provenance ---------------------------------------------------------------

def test_every_run_carries_attributable_provenance():
    """Delegation requires attribution: a run with no provenance is unattributable work."""
    r = run(GOOD, dispatch=_fake([_ok("a"), _ok("a SUPPORTED"), _ok("brief")]))
    p = r["provenance"]
    assert p["run_id"] == r["run_id"]
    assert len(p["content_hash"]) == 64
    assert p["schema_version"] and p["generated_by"] and p["generated_at"]


def test_provenance_survives_a_BLOCKED_run():
    """A halted run must still be attributable — otherwise failures leave no trace."""
    r = run({}, dispatch=_fake([]))
    assert r["outcome"] == Outcome.BLOCKED.value
    assert len(r["provenance"]["content_hash"]) == 64


def test_content_hash_changes_when_evidence_changes():
    r1 = run(GOOD, dispatch=_fake([_ok("a"), _ok("a SUPPORTED"), _ok("brief one")]))
    r2 = run(GOOD, dispatch=_fake([_ok("a"), _ok("a SUPPORTED"), _ok("brief two")]))
    assert r1["provenance"]["content_hash"] != r2["provenance"]["content_hash"]


# --- the module must not mutate factory state --------------------------------

def test_run_does_not_write_readiness_or_health():
    """Founder constraint: a run produces evidence. It never edits the registry."""
    before = (ROOT / "coordination/council/factory_registry.json").read_bytes()
    run(GOOD, dispatch=_fake([_ok("a"), _ok("a SUPPORTED"), _ok("b")]))
    after = (ROOT / "coordination/council/factory_registry.json").read_bytes()
    assert before == after
