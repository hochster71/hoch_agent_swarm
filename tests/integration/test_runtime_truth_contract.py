import time

from backend.final_verifier.runtime_truth_contract import (
    RuntimeTruthContract,
    RuntimeTruthVerdictGuard,
)


def _c():
    return RuntimeTruthContract()


def test_contract_loads():
    c = _c().load()
    assert c["contract_id"] == "HAS-RUNTIME-TRUTH-CONTRACT"
    assert c["only_verified_renders_green"] is True


def test_source_of_truth_hierarchy():
    c = _c()
    # runtime telemetry outranks agent inference
    assert c.resolve_conflict("agent_inference", "runtime_telemetry") == "runtime_telemetry"
    assert c.source_rank("runtime_telemetry") < c.source_rank("operator_assertion")


def test_only_verified_renders_green():
    c = _c()
    assert c.state_renders_green("VERIFIED") is True
    for state in ("CLAIMED", "OBSERVED", "STALE", "UNKNOWN", "BLOCKED"):
        assert c.state_renders_green(state) is False


def test_verified_requires_full_evidence():
    c = _c()
    res = c.validate_label("VERIFIED", ["evidence_paths", "timestamps"])
    assert res["is_valid"] is False
    assert "test_names" in res["missing"]

    full = ["evidence_paths", "timestamps", "test_names",
            "within_freshness_budget", "adversarial_verification"]
    assert c.validate_label("VERIFIED", full)["is_valid"] is True


def test_freshness_budget():
    c = _c()
    now = time.time()
    assert c.is_fresh("runtime_telemetry", now - 100, now) is True   # within 300s
    assert c.is_fresh("runtime_telemetry", now - 600, now) is False  # stale
    assert c.is_fresh("unknown_kind", now, now) is False             # fail closed


def test_tier_gate_proportionality():
    c = _c()
    # T0 is non-blocking -> always passes
    assert c.tier_gate("T0_read_only", [])["is_valid"] is True
    # T1 needs file_diff + unit_test + clean_git_status
    assert c.tier_gate("T1_reversible_local", ["file_diff"])["is_valid"] is False
    assert c.tier_gate(
        "T1_reversible_local",
        ["file_diff", "unit_test", "clean_git_status"],
    )["is_valid"] is True


def test_release_blockers_present():
    c = _c()
    blockers = c.release_blockers()
    assert "fake_green" in blockers
    assert "seeded_fault_not_caught" in blockers


# --- verdict guard (the enforcement hook) --------------------------------

def test_guard_blocks_fake_green():
    g = RuntimeTruthVerdictGuard(not_ready_cap=50.0)
    # green claimed while readiness is at/below not-ready cap -> illegal
    res = g.validate_verdict("VERIFIED", 50.0)
    assert res["is_valid"] is False
    assert "fake_green" in res["violations"][0]
    assert g.validate_verdict("VERIFIED", 30.0)["is_valid"] is False


def test_guard_allows_legitimate_green():
    g = RuntimeTruthVerdictGuard(not_ready_cap=50.0)
    # capped at 90 (e.g. dirty git) but above not-ready floor -> still legal
    assert g.validate_verdict("VERIFIED", 90.0)["is_valid"] is True
    assert g.validate_verdict("VERIFIED", 100.0)["is_valid"] is True


def test_guard_ignores_non_green_status():
    g = RuntimeTruthVerdictGuard(not_ready_cap=50.0)
    # already BLOCKED -> guard never fires, can only tighten green
    assert g.validate_verdict("BLOCKED", 10.0)["is_valid"] is True


def test_guard_fails_open_on_bad_input():
    g = RuntimeTruthVerdictGuard(not_ready_cap=50.0)
    assert g.validate_verdict("VERIFIED", None)["is_valid"] is True
    assert g.validate_verdict("VERIFIED", "n/a")["is_valid"] is True
