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


# =============================================================================
# TRAVERSAL 3 REGRESSIONS (2026-07-21)
# Both defects were unreachable by the tests above: stubs return CLEAN failures, real
# degradation returns dirty ones. These test the two hypotheses the repair asserts.
# =============================================================================

from backend.helm_runtime.hrf_runtime import canonicalize_detail  # noqa: E402


# --- HRF-DEFECT-001 — classification reflects observed PROGRESS, not attempts ---

def test_attempted_but_zero_output_is_NOT_OPERATIONAL_not_PARTIAL():
    """T3 case 3b/3c: the first role ran and failed. Nothing usable was produced.
    Reporting PARTIAL would claim progress that did not occur."""
    d = _fake([{"ok": False, "status": "GATEWAY_ERROR", "message": "model absent"}])
    r = run(GOOD, dispatch=d)
    assert r["outcome"] == Outcome.NOT_OPERATIONAL.value


def test_some_progress_then_failure_is_PARTIAL():
    """T3 case 3a: Researcher produced work, Auditor failed. Materially different from
    3b/3c — and must no longer classify identically."""
    d = _fake([_ok("1. claim A"), {"ok": False, "status": "GATEWAY_ERROR", "message": "down"}])
    r = run(GOOD, dispatch=d)
    assert r["outcome"] == Outcome.PARTIAL.value


def test_3a_and_3b_no_longer_collapse_to_the_same_class():
    """The defect in one line: two runs with different amounts of completed work must not
    receive the same classification."""
    partial = run(GOOD, dispatch=_fake([_ok("work"), {"ok": False, "message": "x"}]))
    none = run(GOOD, dispatch=_fake([{"ok": False, "message": "x"}]))
    assert partial["outcome"] != none["outcome"]


def test_ok_but_empty_output_does_not_count_as_progress():
    """A provider can return ok with empty text. Empty output is not work."""
    r = run(GOOD, dispatch=_fake([{"ok": True, "text": "", "cost": 0.0}]))
    assert r["outcome"] == Outcome.NOT_OPERATIONAL.value


def test_produced_output_is_recorded_per_step():
    r = run(GOOD, dispatch=_fake([_ok("a"), {"ok": False, "message": "x"}]))
    assert r["steps"][0]["produced_output"] is True
    assert r["steps"][1]["produced_output"] is False


# --- HRF-DEFECT-002 — provenance must not depend on terminal formatting ---

DIRTY = "\x1b[?2026h\x1b[?25l\x1b[1G\x1b[K\x1b[?25h model not found"
# Same message, rendered with terminal decoration. NOTE the test below was initially
# written comparing a decorated message that ALSO carried extra provider chatter
# ("pulling manifest") against a plain one, and failed — correctly. Those are not the
# same failure: one contains additional real output. canonicalize_detail removes
# PRESENTATION, not content. Stripping provider progress text by pattern would be
# discarding evidence, so it deliberately does not.


def test_ansi_and_spinner_frames_are_stripped():
    c = canonicalize_detail(DIRTY)
    assert "\x1b" not in c and "⠋" not in c
    assert "model not found" in c


def test_identical_failures_hash_identically_regardless_of_rendering():
    """THE hypothesis. Two semantically identical failures, one rendered with terminal
    control codes — provenance must not diverge on presentation."""
    clean = run(GOOD, dispatch=_fake([{"ok": False, "message": "model not found"}]))
    dirty = run(GOOD, dispatch=_fake([{"ok": False, "message": DIRTY}]))
    assert clean["steps"][0]["detail"] == dirty["steps"][0]["detail"]


def test_canonicalize_is_idempotent():
    once = canonicalize_detail(DIRTY)
    assert canonicalize_detail(once) == once


def test_canonicalize_collapses_whitespace_and_carriage_returns():
    assert canonicalize_detail("a\r\n  b\t\tc") == "a b c"


def test_canonicalize_handles_none_and_non_string():
    assert canonicalize_detail(None) == ""
    assert canonicalize_detail(1234) == "1234"


# =============================================================================
# CYB-002 STEP 2 — the observation window is STRUCTURAL (2026-07-21)
# Evidence that depends on someone remembering to ask for it is not a control.
# =============================================================================

def test_every_mission_emits_an_observation_window_without_being_asked():
    """THE structural property. No flag, no wrapper, no operator discipline."""
    r = run(GOOD, dispatch=_fake([_ok("a"), _ok("a SUPPORTED"), _ok("brief")]))
    o = r["execution_observation"]
    assert o is not None
    assert o["evidence_class"] == "OBSERVED_EXECUTION"
    assert o["observation_windows"] == 1
    assert len(o["content_hash"]) == 64


def test_a_BLOCKED_mission_still_carries_its_observation_field():
    """A halted run must not lose its evidence surface — failures leave traces too."""
    r = run({}, dispatch=_fake([]))
    assert r["outcome"] == Outcome.BLOCKED.value
    assert "execution_observation" in r


def test_disabled_observation_is_RECORDED_not_silent():
    """An absent window and an empty window must never look the same. Turning the
    observer off is itself evidence."""
    r = run(GOOD, dispatch=_fake([_ok("a"), _ok("a SUPPORTED"), _ok("b")]),
            observe_execution=False)
    o = r["execution_observation"]
    assert o["observation"] == "DISABLED"
    assert "observed nothing" in o["note"]


def test_observation_does_not_alter_mission_outcome():
    """The observer must not change what it observes. Same dispatch, same verdict,
    observed or not."""
    obs_on = run(GOOD, dispatch=_fake([_ok("a"), _ok("a SUPPORTED"), _ok("b")]))
    obs_off = run(GOOD, dispatch=_fake([_ok("a"), _ok("a SUPPORTED"), _ok("b")]),
                  observe_execution=False)
    assert obs_on["outcome"] == obs_off["outcome"]
    assert [s["component"] for s in obs_on["steps"]] == \
           [s["component"] for s in obs_off["steps"]]


def test_role_failure_still_stops_the_sequence_after_refactor():
    """The role loop moved into a closure so the window could wrap it. Guard that the
    first-failure-stops behaviour survived the refactor."""
    r = run(GOOD, dispatch=_fake([_ok("a"), {"ok": False, "message": "down"}, _ok("never")]))
    assert len(r["steps"]) == 2, "execution continued past a failed role"
    assert r["outcome"] == Outcome.PARTIAL.value
