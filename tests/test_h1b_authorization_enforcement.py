"""HELM H1B REMEDIATION — the 24 required production-path proofs.

Every test here exercises PRODUCTION code (scripts/council/h1_authorization.py,
scripts/council/aggregate.py, scripts/council/adapters.py). No validator is
reimplemented inside this module -- that was Grok F5, and it is not repeated.

No test makes an external call. Test 23 proves it structurally.
"""
from __future__ import annotations

import copy
import datetime
import json
import multiprocessing
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from council import adapters  # noqa: E402
from scripts.council.aggregate import (  # noqa: E402
    DRY_RUN,
    LIVE_EXTERNAL,
    LOCAL_ONLY,
    MOCK_INTERNAL,
    aggregate,
)
@pytest.fixture
def registry_factory(tmp_path):
    from scripts.council.registry import Registry
    roster = {
        "profiles": {
            "frontier_council": {
                "promotion_capable": False,
                "release_capable": False,
                "required_member_ids": ["chatgpt", "claude", "grok"],
                "allowed_member_ids": ["chatgpt", "claude", "grok"],
                "min_quorum": 0
            },
            "local_proof": {
                "promotion_capable": False,
                "release_capable": False,
                "required_member_ids": ["local_ollama"],
                "allowed_member_ids": ["local_ollama"],
                "min_quorum": 0
            }
        },
        "members": {
            "chatgpt": {"quorum_eligible": True, "enabled": True},
            "claude": {"quorum_eligible": True, "enabled": True},
            "grok": {"quorum_eligible": True, "enabled": True},
            "local_ollama": {"quorum_eligible": True, "enabled": True}
        }
    }
    roster_path = tmp_path / "roster.json"
    contracts_path = tmp_path / "contracts.json"
    roster_path.write_text(json.dumps(roster))
    contracts_path.write_text(json.dumps({}))
    return Registry(roster_path, contracts_path)
from scripts.council.generate_h1_candidate_registry import build as build_registry  # noqa: E402
from scripts.council.h1_authorization import (  # noqa: E402
    ACTIVE_CANDIDATE,
    NON_EXECUTABLE_TEST_PACKAGE,
    PACKAGES_DIR,
    SUPERSEDED_BLOCKED_CANDIDATE,
    AuthorizationError,
    AuthorizationLedger,
    CandidateRegistry,
    H1AuthorizationValidator,
    LedgerError,
    authorize_and_consume,
    credential_matrix,
)

NOW = datetime.datetime(2026, 7, 12, 3, 0, 0, tzinfo=datetime.timezone.utc)
ISSUED = (NOW - datetime.timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
EXPIRES = (NOW + datetime.timedelta(hours=12)).isoformat().replace("+00:00", "Z")
PAST = (NOW - datetime.timedelta(hours=1)).isoformat().replace("+00:00", "Z")

ALL_PRESENT = {
    p: {"credential_reference": f"{p.upper()}_API_KEY", "status": "PRESENT_UNVERIFIED",
        "value_exposed": False}
    for p in ("openai", "anthropic", "xai")
}


# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def registry_doc():
    return build_registry(PACKAGES_DIR)


@pytest.fixture(scope="module")
def active_package_id(registry_doc):
    assert registry_doc["status"] == "RECONCILED", registry_doc.get("reconciliation_errors")
    return registry_doc["authoritative_candidate_package_id"]


@pytest.fixture
def sandbox(tmp_path, registry_doc):
    """Writable copies of the packages tree, registry and ledger. Real tree untouched."""
    packages = tmp_path / "live_proof_packages"
    shutil.copytree(PACKAGES_DIR, packages)
    registry_path = tmp_path / "h1_candidate_registry.json"
    registry_path.write_text(json.dumps(registry_doc, indent=2))
    ledger = AuthorizationLedger(tmp_path / "authorization_ledger.jsonl")
    return {
        "packages": packages,
        "registry": CandidateRegistry(registry_path),
        "registry_path": registry_path,
        "ledger": ledger,
    }


@pytest.fixture
def granted_auth(active_package_id):
    """A HYPOTHETICAL granted authorization, in memory only.

    Never written to coordination/council/frontier_authorization.json. It exists so the
    tests can prove every OTHER defect still blocks even with the founder gate imagined open.
    """
    template = json.loads(
        (PACKAGES_DIR / active_package_id / "founder_authorization.template.json").read_text()
    )
    auth = copy.deepcopy(template)
    auth.update({
        "authorization_status": "GRANTED",
        "issued_at": ISSUED,
        "expires_at": EXPIRES,
        "approval_reference": "TEST-HYPOTHETICAL-NOT-A-REAL-APPROVAL",
    })
    return auth


def _validate(auth, package_id, sb, **kw):
    v = H1AuthorizationValidator(package_id, sb["packages"], sb["registry"])
    return v.validate(
        auth,
        now=kw.pop("now", NOW),
        credentials=kw.pop("credentials", ALL_PRESENT),
        **kw,
    )


def _frontier_results(*, mock: bool, member_ids=("chatgpt", "claude", "grok")):
    providers = {"chatgpt": "openai", "claude": "anthropic", "grok": "openai_compat"}
    models = {"chatgpt": "gpt-5.6-terra", "claude": "claude-sonnet-5", "grok": "grok-4.5"}
    disp, vr = [], {}
    for mid in member_ids:
        disp.append({"member_id": mid, "dispatched": True, "status": "RESPONDED"})
        vr[mid] = {
            "accepted": True, "status": "ACCEPTED", "reasons": [],
            "response": {
                "run_id": "R1", "member_id": mid, "provider": providers[mid],
                "requested_model": models[mid], "resolved_model": models[mid],
                "verdict": "APPROVE", "rationale": "x", "evidence_refs": [],
                "provider_identity_source": "provider_response",
                "resolved_model_source": "provider_response",
                "telemetry": {
                    "is_fallback": False, "is_mock": mock,
                    "adapter_kind": "mock" if mock else "live",
                    "raw_response_sha256": "abc", "raw_response_path": "raw/x.txt",
                },
            },
        }
    return disp, vr


# ==========================================================================
# CANDIDATE REGISTRY  (1, 2, 3)
# ==========================================================================

def test_01_test_package_cannot_become_active_candidate(registry_doc, sandbox):
    tests = [p for p in registry_doc["packages"]
             if p["classification"] == NON_EXECUTABLE_TEST_PACKAGE]
    assert tests, "expected retained test packages"
    for p in tests:
        assert p["authorization_eligible"] is False
        assert sandbox["registry"].is_authorization_eligible(p["package_id"]) is False
        blocks = _validate({"authorization_status": "GRANTED"}, p["package_id"], sandbox)
        assert H1AuthorizationValidator.B_TEST_PACKAGE in blocks


def test_02_superseded_package_cannot_become_active_candidate(registry_doc, sandbox):
    sup = [p for p in registry_doc["packages"]
           if p["classification"] == SUPERSEDED_BLOCKED_CANDIDATE]
    assert sup, "expected retained superseded packages"
    for p in sup:
        assert p["authorization_eligible"] is False
        assert sandbox["registry"].is_authorization_eligible(p["package_id"]) is False
        blocks = _validate({"authorization_status": "GRANTED"}, p["package_id"], sandbox)
        assert H1AuthorizationValidator.B_SUPERSEDED in blocks


def test_03_two_active_candidates_cause_reconciliation_failure(tmp_path, registry_doc,
                                                               active_package_id, granted_auth):
    doc = copy.deepcopy(registry_doc)
    for p in doc["packages"]:                      # forge a second ACTIVE_CANDIDATE
        if p["classification"] == SUPERSEDED_BLOCKED_CANDIDATE:
            p["classification"] = ACTIVE_CANDIDATE
            p["authorization_eligible"] = True
            break
    path = tmp_path / "reg.json"
    path.write_text(json.dumps(doc))

    reg = CandidateRegistry(path)
    assert reg.reconciled is False
    assert reg.status == "EVIDENCE_RECONCILIATION_REQUIRED"
    assert reg.active_candidate() is None
    # and NOTHING is authorizable while the registry disagrees with itself
    assert reg.is_authorization_eligible(active_package_id) is False
    blocks = H1AuthorizationValidator(active_package_id, PACKAGES_DIR, reg).validate(
        granted_auth, now=NOW, credentials=ALL_PRESENT)
    assert H1AuthorizationValidator.B_REGISTRY_UNRECONCILED in blocks


# ==========================================================================
# QUORUM ISOLATION  (4, 5, 18, 19, 20, 21)
# ==========================================================================

def test_04_mock_evidence_cannot_set_frontier_quorum(registry_factory):
    disp, vr = _frontier_results(mock=True)
    agg = aggregate(registry_factory, "frontier_council", disp, vr,
                    execution_mode=MOCK_INTERNAL, authorization_consumed=False)
    assert agg["frontier_council_quorum"] is False
    assert agg["overall_status"] == "MOCK_FRONTIER_CONTRACT_PASS"
    assert agg["promotion_eligible"] is False
    assert agg["safe_to_execute_now"] is False


def test_05_dry_run_evidence_cannot_set_frontier_quorum(registry_factory):
    disp, vr = _frontier_results(mock=True)
    agg = aggregate(registry_factory, "frontier_council", disp, vr,
                    execution_mode=DRY_RUN, authorization_consumed=False)
    assert agg["frontier_council_quorum"] is False
    assert agg["overall_status"] == "DRY_RUN_PACKAGE_PASS"
    assert agg["safe_to_execute_now"] is False


def test_18_local_ollama_cannot_satisfy_frontier_quorum(registry_factory):
    disp = [{"member_id": "local_ollama", "dispatched": True, "status": "RESPONDED"}]
    vr = {"local_ollama": {
        "accepted": True, "status": "ACCEPTED", "reasons": [],
        "response": {"run_id": "R1", "member_id": "local_ollama", "provider": "ollama",
                     "requested_model": "llama3.1:8b", "resolved_model": "llama3.1:8b",
                     "verdict": "APPROVE", "rationale": "x", "evidence_refs": [],
                     "telemetry": {"is_fallback": False, "adapter_kind": "local"}}}}
    agg = aggregate(registry_factory, "local_proof", disp, vr,
                    execution_mode=LOCAL_ONLY, authorization_consumed=False)
    assert agg["local_profile_quorum"] is True      # the local proof is real...
    assert agg["frontier_council_quorum"] is False  # ...and confers nothing frontier
    assert agg["promotion_eligible"] is False
    assert agg["safe_to_execute_now"] is False


def test_19_advisory_records_cannot_satisfy_frontier_quorum(registry_factory):
    from scripts.council.aggregate import advisory_quorum
    records = [{"status": "RECORDED", "authority": "ADVISORY_ONLY", "lane": lane}
               for lane in ("research", "security", "product") for _ in range(3)]
    adv = advisory_quorum(records, {"min_record_count": 1,
                                    "required_lane_distribution": {"research": 1}})
    assert adv["advisory_quorum_achieved"] is True
    assert adv["confers_live_authority"] is False

    agg = aggregate(registry_factory, "frontier_council", [], {}, advisory=adv,
                    execution_mode=MOCK_INTERNAL, authorization_consumed=False)
    assert agg["advisory_quorum"] is True
    assert agg["frontier_council_quorum"] is False
    assert agg["advisory_confers_live_authority"] is False


def test_20_partial_provider_set_cannot_satisfy_frontier_quorum(registry_factory):
    disp, vr = _frontier_results(mock=False, member_ids=("chatgpt", "claude"))  # only 2 of 3
    agg = aggregate(registry_factory, "frontier_council", disp, vr,
                    execution_mode=LIVE_EXTERNAL, authorization_consumed=True)
    assert agg["frontier_council_quorum"] is False
    assert any("DISTINCT_PROVIDERS" in r or "DISTINCT_MEMBERS" in r or "MISSING" in r.upper()
               for r in agg["frontier_live_quorum_blocked_reasons"] + agg["missing_required_members"])


def test_21_live_quorum_cannot_imply_production_promotion(registry_factory):
    disp, vr = _frontier_results(mock=False)
    agg = aggregate(registry_factory, "frontier_council", disp, vr,
                    execution_mode=LIVE_EXTERNAL, authorization_consumed=False)
    # No consumed authorization => no quorum, and certainly no promotion.
    assert agg["frontier_council_quorum"] is False
    assert agg["promotion_eligible"] is False
    assert agg["safe_to_execute_now"] is False
    assert "AUTHORIZATION_NOT_CONSUMED" in agg["frontier_live_quorum_blocked_reasons"]


def test_24_roster_digest_mismatch_blocks_authorization(granted_auth, active_package_id, sandbox):
    digests_path = sandbox["packages"] / active_package_id / "request_digests.json"
    digests = json.loads(digests_path.read_text())
    digests["roster_sha256"] = "0" * 64
    digests_path.write_text(json.dumps(digests))
    assert H1AuthorizationValidator.B_ROSTER_DIGEST in _validate(granted_auth, active_package_id, sandbox)


def test_25_contract_digest_mismatch_blocks_authorization(granted_auth, active_package_id, sandbox):
    digests_path = sandbox["packages"] / active_package_id / "request_digests.json"
    digests = json.loads(digests_path.read_text())
    digests["frontier_contract_sha256"] = "0" * 64
    digests_path.write_text(json.dumps(digests))
    assert H1AuthorizationValidator.B_CONTRACT_DIGEST in _validate(granted_auth, active_package_id, sandbox)


def test_26_missing_digest_blocks_authorization(granted_auth, active_package_id, sandbox):
    digests_path = sandbox["packages"] / active_package_id / "request_digests.json"
    digests = json.loads(digests_path.read_text())
    del digests["model_policy_sha256"]
    digests_path.write_text(json.dumps(digests))
    assert H1AuthorizationValidator.B_MODEL_POLICY_DIGEST in _validate(granted_auth, active_package_id, sandbox)


# ==========================================================================
# AUTHORIZATION BINDING  (6 - 12)
# ==========================================================================

def test_06_wrong_package_id_blocks_authorization(granted_auth, active_package_id, sandbox):
    auth = copy.deepcopy(granted_auth)
    auth["package_id"] = "HELM-H1-CANDIDATE-20260101T000000Z-DEADBEEF"
    assert H1AuthorizationValidator.B_PACKAGE_ID in _validate(auth, active_package_id, sandbox)


def test_07_wrong_authorization_id_blocks_authorization(granted_auth, active_package_id, sandbox):
    auth = copy.deepcopy(granted_auth)
    auth["authorization_id"] = "HELM-H1-AUTH-SOMEONE-ELSES"
    assert H1AuthorizationValidator.B_AUTHORIZATION_ID in _validate(auth, active_package_id, sandbox)


def test_08_wrong_combined_digest_blocks_authorization(granted_auth, active_package_id, sandbox):
    auth = copy.deepcopy(granted_auth)
    auth["combined_authorization_sha256"] = "0" * 64
    assert H1AuthorizationValidator.B_COMBINED_DIGEST in _validate(auth, active_package_id, sandbox)

    missing = copy.deepcopy(granted_auth)
    missing.pop("combined_authorization_sha256")
    assert H1AuthorizationValidator.B_COMBINED_DIGEST in _validate(missing, active_package_id, sandbox)


def test_09_changed_provider_request_blocks_authorization(granted_auth, active_package_id, sandbox):
    req = sandbox["packages"] / active_package_id / "provider_requests" / "claude.request.redacted.json"
    data = json.loads(req.read_text())
    data["max_tokens"] = 999999                      # mutate AFTER review
    req.write_text(json.dumps(data, indent=2))

    blocks = _validate(granted_auth, active_package_id, sandbox)
    assert H1AuthorizationValidator.B_REQUEST_DIGEST in blocks
    assert H1AuthorizationValidator.B_COMBINED_DIGEST in blocks


def test_10_changed_model_blocks_authorization(granted_auth, active_package_id, sandbox):
    auth = copy.deepcopy(granted_auth)
    auth["permitted_models"] = {"openai": "gpt-4o",           # substituted
                                "anthropic": "claude-sonnet-5",
                                "xai": "grok-4.5"}
    assert H1AuthorizationValidator.B_MODEL in _validate(auth, active_package_id, sandbox)

    # and a request for a model the package never signed is refused too
    blocks = _validate(granted_auth, active_package_id, sandbox,
                       requested_models={"openai": "gpt-4o"})
    assert H1AuthorizationValidator.B_MODEL in blocks


def test_11_changed_provider_blocks_authorization(granted_auth, active_package_id, sandbox):
    auth = copy.deepcopy(granted_auth)
    auth["permitted_providers"] = ["openai", "anthropic", "google"]
    assert H1AuthorizationValidator.B_PROVIDER in _validate(auth, active_package_id, sandbox)

    blocks = _validate(granted_auth, active_package_id, sandbox,
                       requested_providers=["openai", "google"])
    assert H1AuthorizationValidator.B_PROVIDER in blocks


def test_12_expired_authorization_blocks_launch(granted_auth, active_package_id, sandbox):
    expired = copy.deepcopy(granted_auth)
    expired["expires_at"] = PAST
    assert H1AuthorizationValidator.B_EXPIRED in _validate(expired, active_package_id, sandbox)

    never = copy.deepcopy(granted_auth)
    never["expires_at"] = None
    assert H1AuthorizationValidator.B_EXPIRED in _validate(never, active_package_id, sandbox)


def test_00_clean_hypothetical_authorization_validates(granted_auth, active_package_id, sandbox):
    """Positive control: without it, every block above could be a false pass."""
    assert _validate(granted_auth, active_package_id, sandbox) == []


# ==========================================================================
# ATOMIC CONSUME + REPLAY LEDGER  (13 - 17)
# ==========================================================================

def _consume(sb, auth, package_id, run_id="RUN-1"):
    return authorize_and_consume(
        authorization=auth, package_id=package_id, run_id=run_id,
        packages_dir=sb["packages"], registry=sb["registry"], ledger=sb["ledger"],
        credentials=ALL_PRESENT, now=NOW,
    )


def test_13_replayed_authorization_blocks_launch(granted_auth, active_package_id, sandbox):
    receipt = _consume(sandbox, granted_auth, active_package_id)
    assert receipt["status"] == "CONSUMED"

    with pytest.raises(AuthorizationError) as exc:      # same authorization, second time
        _consume(sandbox, granted_auth, active_package_id, run_id="RUN-2")
    assert "AUTHORIZATION_REPLAY" in exc.value.blocks

    # ...and the raw ledger API refuses it too, not just the wrapper
    with pytest.raises(LedgerError):
        sandbox["ledger"].consume(
            authorization_id=granted_auth["authorization_id"],
            package_id=active_package_id, run_id="RUN-3", request_digest="x")


def _worker(ledger_path, auth_id, package_id, queue):
    from scripts.council.h1_authorization import AuthorizationLedger, LedgerError
    led = AuthorizationLedger(Path(ledger_path))
    try:
        led.consume(authorization_id=auth_id, package_id=package_id,
                    run_id="CONCURRENT", request_digest="d", lock_timeout=2.0)
        queue.put("CONSUMED")
    except LedgerError as e:
        queue.put(f"BLOCKED:{e}")


def test_14_second_concurrent_consume_blocks(granted_auth, active_package_id, tmp_path):
    ledger_path = tmp_path / "ledger.jsonl"
    auth_id = granted_auth["authorization_id"]
    ctx = multiprocessing.get_context("spawn")
    q = ctx.Queue()
    procs = [ctx.Process(target=_worker, args=(str(ledger_path), auth_id, active_package_id, q))
             for _ in range(2)]
    for p in procs:
        p.start()
    for p in procs:
        p.join(30)

    results = sorted(q.get() for _ in range(2))
    consumed = [r for r in results if r == "CONSUMED"]
    blocked = [r for r in results if r.startswith("BLOCKED")]
    assert len(consumed) == 1, f"exactly one worker may win: {results}"
    assert len(blocked) == 1, f"the loser must be blocked, not silently allowed: {results}"

    entries = AuthorizationLedger(ledger_path).entries()
    assert len([e for e in entries if e["status"] == "CONSUMED"]) == 1


def test_15_authorization_ledger_is_append_only(granted_auth, active_package_id, sandbox):
    ledger = sandbox["ledger"]
    _consume(sandbox, granted_auth, active_package_id)
    first = ledger.path.read_text()
    assert first.count("\n") == 1

    # A second, DIFFERENT authorization appends -- it never rewrites the first line.
    other = copy.deepcopy(granted_auth)
    other["authorization_id"] = "HELM-H1-AUTH-OTHER"
    ledger.consume(authorization_id="HELM-H1-AUTH-OTHER", package_id=active_package_id,
                   run_id="RUN-9", request_digest="d2")
    second = ledger.path.read_text()
    assert second.startswith(first), "prior ledger bytes must be immutable"
    assert second.count("\n") == 2
    assert ledger.is_consumed(granted_auth["authorization_id"]) is True


def test_16_failed_validation_does_not_consume_authorization(granted_auth, active_package_id,
                                                             sandbox):
    bad = copy.deepcopy(granted_auth)
    bad["combined_authorization_sha256"] = "0" * 64     # will fail validation

    with pytest.raises(AuthorizationError):
        _consume(sandbox, bad, active_package_id)

    assert sandbox["ledger"].entries() == []
    assert sandbox["ledger"].is_consumed(granted_auth["authorization_id"]) is False
    # the good authorization is still spendable -- the failure cost nothing
    assert _consume(sandbox, granted_auth, active_package_id)["status"] == "CONSUMED"


def test_17_successful_pre_dispatch_consume_occurs_exactly_once(granted_auth, active_package_id,
                                                                sandbox):
    receipt = _consume(sandbox, granted_auth, active_package_id)
    assert receipt["authorization_id"] == granted_auth["authorization_id"]
    assert receipt["package_id"] == active_package_id
    assert receipt["process_id"] > 0
    assert receipt["consumed_at"].endswith("Z")

    entries = sandbox["ledger"].entries()
    assert len(entries) == 1
    for _ in range(3):
        with pytest.raises(AuthorizationError):
            _consume(sandbox, granted_auth, active_package_id)
    assert len(sandbox["ledger"].entries()) == 1


# ==========================================================================
# UI + EGRESS + SECRETS  (22, 23, 24)
# ==========================================================================

# AUDIT FINDING F-21.3 / II-001 — DO NOT REPLACE THESE FILE READS WITH STRING LITERALS.
#
# Implementation lives in council_router (registered from main) + HelmCouncilView.
# Tests MUST read real files, register routes, and optionally live-request.
# A test that asserts a constant declared five lines above it is a tautology.

def _read_source(*parts: str) -> str:
    path = ROOT.joinpath(*parts)
    assert path.exists(), f"MISSING IMPLEMENTATION FILE: {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf-8")


def test_22_no_ui_field_maps_package_readiness_to_quorum_readiness(tmp_path, monkeypatch):
    # Verify implementation files exist and council_router is registered.
    backend_main = _read_source("backend", "main.py")
    council_impl = _read_source("backend", "instrument_integrity", "council_router.py")
    ui = _read_source("frontend", "src", "components", "helm", "topdown", "HelmCouncilView.tsx")

    assert "council_router" in backend_main, "backend/main.py does not include council_router"
    assert "include_router(council_router)" in backend_main

    # 1. Setup mock environment directories
    import os
    import shutil
    from fastapi.testclient import TestClient
    from backend.main import app

    council_dir = tmp_path / "council"
    council_dir.mkdir()
    packages_dir = council_dir / "live_proof_packages"
    packages_dir.mkdir()

    # Roster & Contracts paths
    roster_path = council_dir / "council_roster.json"
    contracts_path = council_dir / "frontier_seat_contracts.json"
    roster_path.write_text(json.dumps({}))
    contracts_path.write_text(json.dumps({}))

    # Set env var so the backend route uses our sandbox
    monkeypatch.setenv("HELM_COUNCIL_DIR", str(council_dir))

    client = TestClient(app)

    # ----------------------------------------------------------------------
    # Case 5: Missing quorum evidence & missing registry (default fail-closed)
    # ----------------------------------------------------------------------
    r = client.get("/api/v1/council/state")
    assert r.status_code == 200
    body = r.json()
    assert body["package_readiness"] == "FAIL"
    assert body["quorum_readiness"] == "BLOCKED"
    assert body["promotion"] == "LOCKED"
    assert body["safe_to_execute"] == "NO"
    assert "LIVE_PROOF_EVIDENCE_MISSING" in body["blocking_findings"]

    # ----------------------------------------------------------------------
    # Case 1: Package readiness PASS, quorum readiness BLOCKED
    # ----------------------------------------------------------------------
    # Create candidate registry and package
    pkg_id = "HELM-H1-CANDIDATE-20260712T013903Z-4B7F62BE"
    pkg_dir = packages_dir / pkg_id
    pkg_dir.mkdir()

    # Write package files
    (pkg_dir / "prompt.redacted.txt").write_text("prompt content")
    (pkg_dir / "model_policy.json").write_text(json.dumps({"a": 1}))
    (pkg_dir / "budget_limits.json").write_text(json.dumps({"a": 1}))
    (pkg_dir / "pricing_evidence.json").write_text(json.dumps({"a": 1}))
    (pkg_dir / "provider_requests").mkdir()
    for m in ("chatgpt", "claude", "grok"):
        (pkg_dir / "provider_requests" / f"{m}.request.redacted.json").write_text(json.dumps({"model": "m"}))

    # Pre-calculate digests for request_digests.json
    import hashlib
    def canonical_digest(data):
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()

    prompt_sha = hashlib.sha256(b"prompt content").hexdigest()
    model_policy_sha = canonical_digest({"a": 1})
    budget_policy_sha = canonical_digest({"a": 1})
    pricing_evidence_sha = canonical_digest({"a": 1})
    roster_sha = canonical_digest({})
    frontier_contract_sha = canonical_digest({})
    chatgpt_sha = canonical_digest({"model": "m"})
    claude_sha = canonical_digest({"model": "m"})
    grok_sha = canonical_digest({"model": "m"})

    auth_fields = {
        "package_id": pkg_id,
        "provider_list": ["openai", "anthropic", "xai"],
        "exact_models": {
            "openai": "m",
            "anthropic": "m",
            "xai": "m"
        },
        "prompt": "prompt content",
        "chatgpt_request": {"model": "m"},
        "claude_request": {"model": "m"},
        "grok_request": {"model": "m"},
        "budget_limits": {"a": 1},
        "run_count": 1,
        "expires_in_hours": 24,
        "operator_hold_override_scope": "SINGLE_H1_PROOF_ONLY",
        "production_promotion_authorized": False,
        "pricing_evidence": {"a": 1}
    }
    combined_sha = canonical_digest(auth_fields)

    digests = {
        "prompt_sha256": prompt_sha,
        "model_policy_sha256": model_policy_sha,
        "budget_policy_sha256": budget_policy_sha,
        "pricing_evidence_sha256": pricing_evidence_sha,
        "roster_sha256": roster_sha,
        "frontier_contract_sha256": frontier_contract_sha,
        "chatgpt_request_sha256": chatgpt_sha,
        "claude_request_sha256": claude_sha,
        "grok_request_sha256": grok_sha,
        "combined_authorization_sha256": combined_sha
    }
    (pkg_dir / "request_digests.json").write_text(json.dumps(digests))

    # Recompute combined SHA-256 for the candidate package
    from scripts.council.h1b_candidate_registry import recompute_package_integrity
    integrity = recompute_package_integrity(pkg_id, packages_dir)
    assert integrity["integrity_status"] == "PASS"

    # Write registry JSON
    registry_data = {
        "schema_version": "1.0",
        "generated_at": "2026-07-12T02:00:00Z",
        "status": "RECONCILED",
        "authoritative_candidate_package_id": pkg_id,
        "candidate_count": 1,
        "packages": [
            {
                "package_id": pkg_id,
                "classification": "ACTIVE_CANDIDATE",
                "authorization_eligible": True,
                "execution_eligible": False,
                "reason": "OK"
            }
        ]
    }
    (council_dir / "h1_candidate_registry.json").write_text(json.dumps(registry_data))

    # Mock live state where quorum is False
    live_state_data = {
        "run_id": "RUN-1",
        "completed_at": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "aggregation": {
            "overall_status": "BLOCKED_NO_QUORUM",
            "frontier_council_quorum": False,
            "promotion_eligible": False,
            "safe_to_execute_now": False,
            "execution_mode": "LIVE_EXTERNAL"
        }
    }
    (council_dir / "council_live_state.json").write_text(json.dumps(live_state_data))

    r = client.get("/api/v1/council/state")
    assert r.status_code == 200
    body = r.json()
    assert body["package_readiness"] == "PASS"
    assert body["quorum_readiness"] == "BLOCKED"
    assert body["promotion"] == "LOCKED"
    assert body["safe_to_execute"] == "NO"

    # ----------------------------------------------------------------------
    # Case 2: Package readiness PASS, quorum readiness UNKNOWN (missing evidence)
    # ----------------------------------------------------------------------
    # Remove live state file
    (council_dir / "council_live_state.json").unlink()
    r = client.get("/api/v1/council/state")
    assert r.status_code == 200
    body = r.json()
    assert body["package_readiness"] == "PASS"
    assert body["quorum_readiness"] == "BLOCKED"
    assert body["evidence_state"] == "UNKNOWN"

    # ----------------------------------------------------------------------
    # Case 3: Package readiness FAIL, quorum readiness PASS (independent states)
    # ----------------------------------------------------------------------
    # Force package integrity failure (which causes package_readiness to FAIL)
    prompt_file = pkg_dir / "prompt.redacted.txt"
    prompt_content = prompt_file.read_text()
    prompt_file.unlink()

    # Write a successful live state file
    live_state_data["aggregation"]["overall_status"] = "PASS"
    live_state_data["aggregation"]["frontier_council_quorum"] = True
    live_state_data["aggregation"]["safe_to_execute_now"] = True
    live_state_data["completed_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    (council_dir / "council_live_state.json").write_text(json.dumps(live_state_data))

    r = client.get("/api/v1/council/state")
    assert r.status_code == 200
    body = r.json()
    assert body["package_readiness"] == "FAIL"
    assert body["quorum_readiness"] == "PASS"

    # Restore package integrity
    prompt_file.write_text(prompt_content)

    # ----------------------------------------------------------------------
    # Case 4: Stale quorum evidence
    # ----------------------------------------------------------------------
    stale_time = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=600)).isoformat().replace("+00:00", "Z")
    live_state_data["completed_at"] = stale_time
    (council_dir / "council_live_state.json").write_text(json.dumps(live_state_data))

    r = client.get("/api/v1/council/state")
    assert r.status_code == 200
    body = r.json()
    assert body["freshness_state"] == "STALE"
    assert body["quorum_readiness"] == "STALE"

    # ----------------------------------------------------------------------
    # Case 6: Mock evidence excluded
    # ----------------------------------------------------------------------
    # Restore freshness
    live_state_data["completed_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    # Make execution mode non-live
    live_state_data["aggregation"]["execution_mode"] = "MOCK_INTERNAL"
    live_state_data["aggregation"]["overall_status"] = "MOCK_FRONTIER_CONTRACT_PASS"
    (council_dir / "council_live_state.json").write_text(json.dumps(live_state_data))

    r = client.get("/api/v1/council/state")
    assert r.status_code == 200
    body = r.json()
    assert body["quorum_readiness"] == "BLOCKED"
    assert "QUORUM_CONTAINS_MOCK_EVIDENCE:MOCK_FRONTIER_CONTRACT_PASS" in body["blocking_findings"]

    # ----------------------------------------------------------------------
    # Case 7: Malformed backend payload
    # ----------------------------------------------------------------------
    (council_dir / "council_live_state.json").write_text("malformed json {")
    r = client.get("/api/v1/council/state")
    assert r.status_code == 200
    body = r.json()
    assert body["evidence_state"] == "INVALID"
    assert body["quorum_readiness"] == "BLOCKED"

    # ----------------------------------------------------------------------
    # Case 8: Backend exception (gracefully handled)
    # ----------------------------------------------------------------------
    import scripts.council.h1b_candidate_registry as h1b_reg
    def mock_raise():
        raise ValueError("Simulated backend error")
    monkeypatch.setattr(h1b_reg, "reconcile_candidates", mock_raise)
    r = client.get("/api/v1/council/state")
    assert r.status_code == 200
    body = r.json()
    assert body["package_readiness"] == "UNKNOWN"
    assert "Simulated backend error" in body["reason"]

    # ----------------------------------------------------------------------
    # Case 9: Frontend renders each state without promotion
    # ----------------------------------------------------------------------
    assert "fetch(STATE_URL" in ui or "fetch('/api/v1/council/state'" in ui
    assert "promotion" in ui
    assert "state.promotion" in ui
    assert "package_readiness" in ui
    assert "quorum_readiness" in ui
    assert "safe_to_execute" in ui

    # ----------------------------------------------------------------------
    # Case 10: Promotion remains LOCKED unless all required gates pass
    # ----------------------------------------------------------------------
    # If any gate is not PASS (like operator hold is ACTIVE, or registry is not reconciled, or quorum is missing, or harness says promotion_eligible is False), promotion remains LOCKED.
    (council_dir / "h1_candidate_registry.json").write_text(json.dumps(registry_data))

    # Write founder decision
    decision_data = {
        "authorization_id": "HELM-H1-AUTH-20260712T013903Z-4B7F62BE",
        "authorization_status": "GRANTED",
        "package_id": pkg_id,
        "expires_at": (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)).isoformat()
    }
    (council_dir / "h1b_founder_decision.json").write_text(json.dumps(decision_data))

    # Write consumed entry to ledger
    ledger_path = council_dir / "authorization_ledger.jsonl"
    ledger_entry = {
        "authorization_id": "HELM-H1-AUTH-20260712T013903Z-4B7F62BE",
        "package_id": pkg_id,
        "run_id": "RUN-1",
        "status": "CONSUMED",
        "process_start_time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "consumed_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    ledger_path.write_text(json.dumps(ledger_entry) + "\n")
    monkeypatch.setenv("HELM_AUTH_LEDGER", str(ledger_path))

    r = client.get("/api/v1/council/state")
    assert r.status_code == 200
    body = r.json()
    assert body["promotion"] == "LOCKED"



def test_23_no_external_dispatch_occurs_in_tests():
    # The egress ticket is closed, so any non-loopback POST raises before touching urllib.
    assert adapters.external_egress_open() is False
    with pytest.raises(adapters.ExternalEgressBlocked):
        adapters._http("https://api.openai.com/v1/chat/completions", b"{}", {}, 5)
    with pytest.raises(adapters.ExternalEgressBlocked):
        adapters._http("https://api.anthropic.com/v1/messages", b"{}", {}, 5)

    # Loopback (local Ollama) is permitted with no ticket -- local stays local.
    assert adapters._is_loopback("http://127.0.0.1:11434/api/chat") is True
    assert adapters._is_loopback("https://api.x.ai/v1/chat/completions") is False

    # Live dispatch is hard-disabled during H1B, so the ticket cannot even be opened.
    from scripts.council.h1_authorization import dispatch_live_permitted
    assert dispatch_live_permitted() is False

    # A frontier seat resolves to the MOCK adapter and declares itself as such -- it
    # makes no external call, and aggregate.py refuses to count it as live evidence.
    from tests.doubles.adapters import DummyMockAdapter
    frontier_seat = {"member_id": "chatgpt", "adapter": "openai", "provider": "openai",
                     "requested_model": "gpt-5.6-terra", "endpoint": "https://api.openai.com/v1",
                     "timeout_seconds": 5, "schema_version": "1.0", "role": "reviewer"}
    _text, _resolved, _raw, meta = adapters.dispatch_ex(
        frontier_seat, "RUN ID: R1\nprompt", key="unused", adapter_override=DummyMockAdapter())
    assert meta["adapter_kind"] == "mock"
    assert meta["is_mock"] is True
    assert meta["external_call"] is False

    # A NON-frontier external seat has no mock to fall back to: it is refused outright.
    external_seat = {"member_id": "gemini", "adapter": "gemini", "provider": "google",
                     "requested_model": "gemini-2.5-pro",
                     "endpoint": "https://generativelanguage.googleapis.com/v1beta",
                     "timeout_seconds": 5}
    with pytest.raises(adapters.ExternalEgressBlocked):
        adapters.dispatch_ex(external_seat, "prompt", key="unused")

    # And opening an egress ticket is impossible while H1B holds the gate shut.
    with pytest.raises(adapters.ExternalEgressBlocked):
        with adapters.open_external_egress(
            authorization={"authorization_status": "GRANTED"},
            package_id="X", run_id="R", permitted_providers=[], permitted_models={},
        ):
            pass  # pragma: no cover -- unreachable


def test_24_no_secret_values_appear_in_artifacts():
    # Existence check only: a value placed in the env never reaches the matrix.
    matrix = credential_matrix({"OPENAI_API_KEY": "sk-live-MUST-NEVER-APPEAR"})
    blob = json.dumps(matrix)
    assert "sk-live" not in blob
    assert matrix["openai"]["status"] == "PRESENT_UNVERIFIED"
    assert all(v["value_exposed"] is False for v in matrix.values())

    # No committed council artifact carries a bearer-token-shaped value.
    forbidden = ("sk-ant-", "sk-proj-", "xai-", "Bearer ")
    scanned = 0
    for path in (ROOT / "coordination" / "council").rglob("*"):
        if not path.is_file() or path.suffix not in (".json", ".jsonl", ".txt"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for marker in forbidden:
            assert marker not in text, f"possible secret value in {path}"
        scanned += 1
    assert scanned > 0
