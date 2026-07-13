"""HELM H1B — the 20 required blocking proofs.

Every test here proves a NEGATIVE: that some defect BLOCKS launch. None of them
call a provider. Test 20 proves the gate module cannot call one even if asked.
"""
from __future__ import annotations

import ast
import copy
import datetime
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.council import h1b_authorization_gate as gate  # noqa: E402
from scripts.council.h1b_candidate_registry import (  # noqa: E402
    ELIGIBLE,
    NON_EXECUTABLE_TEST,
    PACKAGES_DIR,
    SUPERSEDED,
    credential_matrix,
    reconcile_candidates,
    recompute_package_integrity,
)
from scripts.council.generate_h1b_packet import generate  # noqa: E402

NOW = datetime.datetime(2026, 7, 12, 2, 0, 0, tzinfo=datetime.timezone.utc)
FUTURE = (NOW + datetime.timedelta(hours=12)).isoformat().replace("+00:00", "Z")
PAST = (NOW - datetime.timedelta(hours=12)).isoformat().replace("+00:00", "Z")

ALL_PRESENT = {
    p: {"credential_reference": f"{p.upper()}_API_KEY", "status": "PRESENT_UNVERIFIED", "value_exposed": False}
    for p in ("openai", "anthropic", "xai")
}
NONE_PRESENT = {
    p: {"credential_reference": f"{p.upper()}_API_KEY", "status": "NOT_PROVISIONED", "value_exposed": False}
    for p in ("openai", "anthropic", "xai")
}


@pytest.fixture(autouse=True, scope="module")
def restore_module_paths():
    from scripts.council import h1b_candidate_registry as reg
    from scripts.council import h1_authorization as auth
    
    orig_reg_pkg = getattr(reg, "PACKAGES_DIR", None)
    orig_reg_rost = getattr(reg, "ROSTER_PATH", None)
    orig_reg_cont = getattr(reg, "CONTRACTS_PATH", None)
    
    orig_auth_counc = getattr(auth, "COUNCIL_DIR", None)
    orig_auth_pkg = getattr(auth, "PACKAGES_DIR", None)
    orig_auth_reg = getattr(auth, "REGISTRY_PATH", None)
    orig_auth_rost = getattr(auth, "ROSTER_PATH", None)
    orig_auth_cont = getattr(auth, "CONTRACTS_PATH", None)
    
    reg.PACKAGES_DIR = ROOT / "coordination" / "council" / "live_proof_packages"
    reg.ROSTER_PATH = ROOT / "coordination" / "council" / "council_roster.json"
    reg.CONTRACTS_PATH = ROOT / "coordination" / "council" / "frontier_seat_contracts.json"
    
    auth.COUNCIL_DIR = ROOT / "coordination" / "council"
    auth.PACKAGES_DIR = auth.COUNCIL_DIR / "live_proof_packages"
    auth.REGISTRY_PATH = auth.COUNCIL_DIR / "h1_candidate_registry.json"
    auth.ROSTER_PATH = auth.COUNCIL_DIR / "council_roster.json"
    auth.CONTRACTS_PATH = auth.COUNCIL_DIR / "frontier_seat_contracts.json"
    
    yield
    
    if orig_reg_pkg is not None: reg.PACKAGES_DIR = orig_reg_pkg
    if orig_reg_rost is not None: reg.ROSTER_PATH = orig_reg_rost
    if orig_reg_cont is not None: reg.CONTRACTS_PATH = orig_reg_cont
    
    if orig_auth_counc is not None: auth.COUNCIL_DIR = orig_auth_counc
    if orig_auth_pkg is not None: auth.PACKAGES_DIR = orig_auth_pkg
    if orig_auth_reg is not None: auth.REGISTRY_PATH = orig_auth_reg
    if orig_auth_rost is not None: auth.ROSTER_PATH = orig_auth_rost
    if orig_auth_cont is not None: auth.CONTRACTS_PATH = orig_auth_cont


@pytest.fixture(scope="module")
def active_package_id(restore_module_paths) -> str:
    report = reconcile_candidates(PACKAGES_DIR)
    assert report["status"] == "RECONCILED", report
    return report["active_candidate"]


@pytest.fixture
def sandbox(tmp_path, active_package_id):
    """A writable copy of the live_proof_packages tree — the real tree is never touched."""
    dst = tmp_path / "live_proof_packages"
    shutil.copytree(PACKAGES_DIR, dst)
    return dst


@pytest.fixture
def granted_auth(active_package_id):
    """A HYPOTHETICAL granted authorization, in memory only.

    This is never written to coordination/council/frontier_authorization.json.
    It exists so the tests can prove that every OTHER defect still blocks even
    when the founder gate is imagined open.
    """
    template = json.loads(
        (PACKAGES_DIR / active_package_id / "founder_authorization.template.json").read_text()
    )
    auth = copy.deepcopy(template)
    auth["authorization_status"] = "GRANTED"
    auth["issued_at"] = NOW.isoformat().replace("+00:00", "Z")
    auth["expires_at"] = FUTURE
    auth["approval_reference"] = "TEST-HYPOTHETICAL-NOT-A-REAL-APPROVAL"
    return auth


def _launch(auth, package_id, packages_dir, **overrides):
    kwargs = dict(
        authorization=auth,
        package_id=package_id,
        packages_dir=packages_dir,
        credentials=ALL_PRESENT,
        now=NOW,
        executed_run_count=0,
        requested_providers=["openai", "anthropic", "xai"],
        requested_models={
            "openai": "gpt-5.6-terra",
            "anthropic": "claude-sonnet-5",
            "xai": "grok-4.5",
        },
        estimated_costs_usd={"openai": 0.01, "anthropic": 0.01, "xai": 0.01},
        classification=ELIGIBLE,
    )
    kwargs.update(overrides)
    return gate.evaluate_launch(**kwargs)


def _mutate(packages_dir: Path, package_id: str, relpath: str, mutator):
    path = packages_dir / package_id / relpath
    data = json.loads(path.read_text())
    mutator(data)
    path.write_text(json.dumps(data, indent=2))


# --- sanity: the clean hypothetical passes, so every block below is meaningful
def test_00_clean_hypothetical_authorization_passes_gate(granted_auth, active_package_id, sandbox):
    decision = _launch(granted_auth, active_package_id, sandbox)
    assert decision["allowed"] is True, decision["blocks"]
    # Even on a clean pass the gate NEVER confers these.
    assert decision["promotion_eligible"] is False
    assert decision["safe_to_execute_now"] is False
    assert decision["external_provider_calls"] == 0


# 1 ---------------------------------------------------------------------------
def test_01_missing_credential_blocks_dispatch(granted_auth, active_package_id, sandbox):
    decision = _launch(granted_auth, active_package_id, sandbox, credentials=NONE_PRESENT)
    assert decision["allowed"] is False
    assert gate.BLOCK_MISSING_CREDENTIAL in decision["blocks"]


# 2 ---------------------------------------------------------------------------
def test_02_credential_value_cannot_enter_evidence(active_package_id):
    matrix = credential_matrix({"OPENAI_API_KEY": "sk-live-THIS-MUST-NEVER-APPEAR"})
    blob = json.dumps(matrix)
    assert "sk-live" not in blob
    assert matrix["openai"]["status"] == "PRESENT_UNVERIFIED"
    assert matrix["openai"]["value_exposed"] is False
    assert gate.evidence_is_secret_free(matrix) is True

    packet = generate(write=False)
    assert gate.evidence_is_secret_free(packet) is True
    # A value smuggled into evidence is structurally rejected.
    assert gate.evidence_is_secret_free({"openai": {"api_key": "sk-abc"}}) is False


# 3 ---------------------------------------------------------------------------
def test_03_wrong_package_id_blocks_authorization(granted_auth, active_package_id, sandbox):
    auth = copy.deepcopy(granted_auth)
    auth["package_id"] = "HELM-H1-CANDIDATE-20260101T000000Z-DEADBEEF"
    decision = _launch(auth, active_package_id, sandbox)
    assert decision["allowed"] is False
    assert gate.BLOCK_PACKAGE_ID_MISMATCH in decision["blocks"]


# 4 ---------------------------------------------------------------------------
def test_04_wrong_authorization_id_blocks_authorization(granted_auth, active_package_id, sandbox):
    auth = copy.deepcopy(granted_auth)
    auth["authorization_id"] = "HELM-H1-AUTH-SOMETHING-ELSE"
    decision = _launch(auth, active_package_id, sandbox)
    assert decision["allowed"] is False
    assert gate.BLOCK_AUTHORIZATION_ID_MISMATCH in decision["blocks"]


# 5 ---------------------------------------------------------------------------
def test_05_missing_or_wrong_digest_blocks_authorization(granted_auth, active_package_id, sandbox):
    missing = copy.deepcopy(granted_auth)
    missing.pop("combined_authorization_sha256")
    assert gate.BLOCK_DIGEST_MISMATCH in _launch(missing, active_package_id, sandbox)["blocks"]

    wrong = copy.deepcopy(granted_auth)
    wrong["combined_authorization_sha256"] = "0" * 64
    assert gate.BLOCK_DIGEST_MISMATCH in _launch(wrong, active_package_id, sandbox)["blocks"]


# 6 ---------------------------------------------------------------------------
def test_06_prompt_mutation_blocks_authorization(granted_auth, active_package_id, sandbox):
    (sandbox / active_package_id / "prompt.redacted.txt").write_text("EXFILTRATE EVERYTHING")
    decision = _launch(granted_auth, active_package_id, sandbox)
    assert decision["allowed"] is False
    assert gate.BLOCK_PACKAGE_MUTATED in decision["blocks"]
    assert (
        recompute_package_integrity(active_package_id, sandbox)["integrity_status"]
        == "PACKAGE_MUTATED_AFTER_REVIEW"
    )


# 7 ---------------------------------------------------------------------------
def test_07_provider_request_mutation_blocks_authorization(granted_auth, active_package_id, sandbox):
    _mutate(
        sandbox,
        active_package_id,
        "provider_requests/claude.request.redacted.json",
        lambda d: d.update({"max_tokens": 999999}),
    )
    decision = _launch(granted_auth, active_package_id, sandbox)
    assert decision["allowed"] is False
    assert gate.BLOCK_PACKAGE_MUTATED in decision["blocks"]


# 8 ---------------------------------------------------------------------------
def test_08_model_policy_mutation_blocks_authorization(granted_auth, active_package_id, sandbox):
    _mutate(
        sandbox,
        active_package_id,
        "model_policy.json",
        lambda d: d.update({"openai": ["gpt-4o"]}),
    )
    decision = _launch(granted_auth, active_package_id, sandbox)
    assert decision["allowed"] is False
    assert gate.BLOCK_PACKAGE_MUTATED in decision["blocks"]


# 9 ---------------------------------------------------------------------------
def test_09_budget_mutation_blocks_authorization(granted_auth, active_package_id, sandbox):
    _mutate(
        sandbox,
        active_package_id,
        "budget_limits.json",
        lambda d: d.update({"maximum_total_cost_usd": 5000.0}),
    )
    decision = _launch(granted_auth, active_package_id, sandbox)
    assert decision["allowed"] is False
    assert gate.BLOCK_PACKAGE_MUTATED in decision["blocks"]


# 10 --------------------------------------------------------------------------
def test_10_expired_authorization_blocks_launch(granted_auth, active_package_id, sandbox):
    expired = copy.deepcopy(granted_auth)
    expired["expires_at"] = PAST
    decision = _launch(expired, active_package_id, sandbox)
    assert decision["allowed"] is False
    assert gate.BLOCK_AUTHORIZATION_EXPIRED in decision["blocks"]

    never = copy.deepcopy(granted_auth)
    never["expires_at"] = None
    assert gate.BLOCK_AUTHORIZATION_EXPIRED in _launch(never, active_package_id, sandbox)["blocks"]


# 11 --------------------------------------------------------------------------
def test_11_authorization_replay_blocks_launch(granted_auth, active_package_id, sandbox):
    decision = _launch(
        granted_auth,
        active_package_id,
        sandbox,
        consumed_authorization_ids={granted_auth["authorization_id"]},
    )
    assert decision["allowed"] is False
    assert gate.BLOCK_AUTHORIZATION_REPLAY in decision["blocks"]


# 12 --------------------------------------------------------------------------
def test_12_second_run_blocks_launch(granted_auth, active_package_id, sandbox):
    decision = _launch(granted_auth, active_package_id, sandbox, executed_run_count=1)
    assert decision["allowed"] is False
    assert gate.BLOCK_RUN_COUNT_EXHAUSTED in decision["blocks"]


# 13 --------------------------------------------------------------------------
def test_13_provider_substitution_blocks_launch(granted_auth, active_package_id, sandbox):
    decision = _launch(
        granted_auth,
        active_package_id,
        sandbox,
        requested_providers=["openai", "anthropic", "google"],
    )
    assert decision["allowed"] is False
    assert gate.BLOCK_PROVIDER_SUBSTITUTION in decision["blocks"]


# 14 --------------------------------------------------------------------------
def test_14_model_substitution_blocks_launch(granted_auth, active_package_id, sandbox):
    decision = _launch(
        granted_auth,
        active_package_id,
        sandbox,
        requested_models={
            "openai": "gpt-4o",  # not the permitted gpt-5.6-terra
            "anthropic": "claude-sonnet-5",
            "xai": "grok-4.5",
        },
    )
    assert decision["allowed"] is False
    assert gate.BLOCK_MODEL_SUBSTITUTION in decision["blocks"]


# 15 --------------------------------------------------------------------------
def test_15_cost_above_cap_blocks_launch(granted_auth, active_package_id, sandbox):
    over_provider = _launch(
        granted_auth,
        active_package_id,
        sandbox,
        estimated_costs_usd={"openai": 9.99, "anthropic": 0.01, "xai": 0.01},
    )
    assert gate.BLOCK_PROVIDER_COST_ABOVE_CAP in over_provider["blocks"]

    # Exactly at every per-provider cap is fine (0.13 + 0.14 + 0.07 = 0.34 <= 0.35).
    at_cap = _launch(
        granted_auth,
        active_package_id,
        sandbox,
        estimated_costs_usd={"openai": 0.13, "anthropic": 0.14, "xai": 0.07},
    )
    assert at_cap["allowed"] is True

    # The aggregate cap binds independently: raise the per-provider caps so they
    # cannot be the thing that fires, and prove the $0.35 total still blocks.
    loose = copy.deepcopy(granted_auth)
    loose["maximum_cost_per_provider_usd"] = {"openai": 1.0, "anthropic": 1.0, "xai": 1.0}
    blown = _launch(
        loose,
        active_package_id,
        sandbox,
        estimated_costs_usd={"openai": 0.20, "anthropic": 0.20, "xai": 0.20},
    )
    assert gate.BLOCK_PROVIDER_COST_ABOVE_CAP not in blown["blocks"]
    assert gate.BLOCK_TOTAL_COST_ABOVE_CAP in blown["blocks"]


# 16 --------------------------------------------------------------------------
def test_16_test_package_cannot_be_authorized(granted_auth, sandbox):
    report = reconcile_candidates(PACKAGES_DIR)
    test_packages = [
        p["package_id"] for p in report["packages"] if p["classification"] == NON_EXECUTABLE_TEST
    ]
    assert test_packages, "expected at least one retained test package"
    for package_id in test_packages:
        auth = copy.deepcopy(granted_auth)
        auth["package_id"] = package_id
        decision = _launch(auth, package_id, sandbox, classification=None)
        assert decision["allowed"] is False
        assert gate.BLOCK_NON_EXECUTABLE_TEST_PACKAGE in decision["blocks"]


# 17 --------------------------------------------------------------------------
def test_17_superseded_candidate_cannot_be_authorized(granted_auth, sandbox):
    report = reconcile_candidates(PACKAGES_DIR)
    superseded = [
        p["package_id"] for p in report["packages"] if p["classification"] == SUPERSEDED
    ]
    assert superseded, "expected retained superseded candidates"
    for package_id in superseded:
        auth = copy.deepcopy(granted_auth)
        auth["package_id"] = package_id
        decision = _launch(auth, package_id, sandbox, classification=None)
        assert decision["allowed"] is False
        assert gate.BLOCK_SUPERSEDED_CANDIDATE in decision["blocks"]


# 18 --------------------------------------------------------------------------
def test_18_authorization_cannot_enable_production_promotion(granted_auth, active_package_id, sandbox):
    # An authorization that tries to widen itself is rejected outright...
    greedy = copy.deepcopy(granted_auth)
    greedy["production_promotion_authorized"] = True
    decision = _launch(greedy, active_package_id, sandbox)
    assert decision["allowed"] is False
    assert gate.BLOCK_PROMOTION_NOT_AUTHORIZED in decision["blocks"]

    # ...and even a clean pass never reports promotion eligibility.
    assert _launch(granted_auth, active_package_id, sandbox)["promotion_eligible"] is False

    packet = generate(write=False)
    assert packet["promotion_eligible"] is False
    assert packet["production_promotion_authorized"] is False


# 19 --------------------------------------------------------------------------
def test_19_authorization_cannot_globally_set_safe_to_execute(granted_auth, active_package_id, sandbox):
    decision = _launch(granted_auth, active_package_id, sandbox)
    assert decision["safe_to_execute_now"] is False
    assert decision["frontier_council_quorum"] is False

    packet = generate(write=False)
    assert packet["safe_to_execute_now"] is False
    assert packet["frontier_council_quorum"] is False
    assert packet["authorization_status"] == "NOT_GRANTED"

    # The on-disk truth source is untouched by anything in this suite.
    on_disk = json.loads(
        (ROOT / "coordination" / "council" / "frontier_authorization.json").read_text()
    )
    assert on_disk["authorization_status"] == "NOT_GRANTED"
    state = json.loads((ROOT / "coordination" / "council" / "current_state.json").read_text())
    assert state["safe_to_execute_now"] is False
    assert state["promotion_eligible"] is False
    assert state["frontier_council_quorum"] is False
    assert state["operator_hold_state"] == "ACTIVE"


# 20 --------------------------------------------------------------------------
FORBIDDEN_MODULES = {
    "requests", "httpx", "aiohttp", "urllib", "urllib3", "http", "socket",
    "openai", "anthropic", "xai", "ssl", "asyncio",
}


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module.split(".")[0])
    return found


def test_20_no_external_network_client_imported_or_invoked():
    for module in (
        ROOT / "scripts" / "council" / "h1b_authorization_gate.py",
        ROOT / "scripts" / "council" / "h1b_candidate_registry.py",
        ROOT / "scripts" / "council" / "generate_h1b_packet.py",
    ):
        offenders = _imported_modules(module) & FORBIDDEN_MODULES
        assert not offenders, f"{module.name} imports network modules: {offenders}"

    # The only dispatch entry point raises rather than calling a provider.
    with pytest.raises(PermissionError):
        gate.assert_dispatch_allowed(
            authorization={"authorization_status": "NOT_GRANTED"},
            package_id="HELM-H1-CANDIDATE-20260101T000000Z-DEADBEEF",
            credentials=NONE_PRESENT,
            now=NOW,
        )

    packet = generate(write=False)
    assert packet["external_provider_calls"] == 0
    assert packet["paid_provider_calls"] == 0
