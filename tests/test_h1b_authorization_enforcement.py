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
from council.aggregate import (  # noqa: E402
    DRY_RUN,
    LIVE_EXTERNAL,
    LOCAL_ONLY,
    MOCK_INTERNAL,
    aggregate,
)
from council.registry import Registry  # noqa: E402
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

def test_04_mock_evidence_cannot_set_frontier_quorum():
    disp, vr = _frontier_results(mock=True)
    agg = aggregate(Registry(), "frontier_council", disp, vr,
                    execution_mode=MOCK_INTERNAL, authorization_consumed=False)
    assert agg["frontier_council_quorum"] is False
    assert agg["overall_status"] == "MOCK_FRONTIER_CONTRACT_PASS"
    assert agg["promotion_eligible"] is False
    assert agg["safe_to_execute_now"] is False


def test_05_dry_run_evidence_cannot_set_frontier_quorum():
    disp, vr = _frontier_results(mock=True)
    agg = aggregate(Registry(), "frontier_council", disp, vr,
                    execution_mode=DRY_RUN, authorization_consumed=False)
    assert agg["frontier_council_quorum"] is False
    assert agg["overall_status"] == "DRY_RUN_PACKAGE_PASS"
    assert agg["safe_to_execute_now"] is False


def test_18_local_ollama_cannot_satisfy_frontier_quorum():
    disp = [{"member_id": "local_ollama", "dispatched": True, "status": "RESPONDED"}]
    vr = {"local_ollama": {
        "accepted": True, "status": "ACCEPTED", "reasons": [],
        "response": {"run_id": "R1", "member_id": "local_ollama", "provider": "ollama",
                     "requested_model": "llama3.1:8b", "resolved_model": "llama3.1:8b",
                     "verdict": "APPROVE", "rationale": "x", "evidence_refs": [],
                     "telemetry": {"is_fallback": False, "adapter_kind": "local"}}}}
    agg = aggregate(Registry(), "local_proof", disp, vr,
                    execution_mode=LOCAL_ONLY, authorization_consumed=False)
    assert agg["local_profile_quorum"] is True      # the local proof is real...
    assert agg["frontier_council_quorum"] is False  # ...and confers nothing frontier
    assert agg["promotion_eligible"] is False
    assert agg["safe_to_execute_now"] is False


def test_19_advisory_records_cannot_satisfy_frontier_quorum():
    from council.aggregate import advisory_quorum
    records = [{"status": "RECORDED", "authority": "ADVISORY_ONLY", "lane": lane}
               for lane in ("research", "security", "product") for _ in range(3)]
    adv = advisory_quorum(records, {"min_record_count": 1,
                                    "required_lane_distribution": {"research": 1}})
    assert adv["advisory_quorum_achieved"] is True
    assert adv["confers_live_authority"] is False

    agg = aggregate(Registry(), "frontier_council", [], {}, advisory=adv,
                    execution_mode=MOCK_INTERNAL, authorization_consumed=False)
    assert agg["advisory_quorum"] is True
    assert agg["frontier_council_quorum"] is False
    assert agg["advisory_confers_live_authority"] is False


def test_20_partial_provider_set_cannot_satisfy_frontier_quorum():
    disp, vr = _frontier_results(mock=False, member_ids=("chatgpt", "claude"))  # only 2 of 3
    agg = aggregate(Registry(), "frontier_council", disp, vr,
                    execution_mode=LIVE_EXTERNAL, authorization_consumed=True)
    assert agg["frontier_council_quorum"] is False
    assert any("DISTINCT_PROVIDERS" in r or "DISTINCT_MEMBERS" in r or "MISSING" in r.upper()
               for r in agg["frontier_live_quorum_blocked_reasons"] + agg["missing_required_members"])


def test_21_live_quorum_cannot_imply_production_promotion():
    disp, vr = _frontier_results(mock=False)
    agg = aggregate(Registry(), "frontier_council", disp, vr,
                    execution_mode=LIVE_EXTERNAL, authorization_consumed=False)
    # No consumed authorization => no quorum, and certainly no promotion.
    assert agg["frontier_council_quorum"] is False
    assert agg["promotion_eligible"] is False
    assert agg["safe_to_execute_now"] is False
    assert "AUTHORIZATION_NOT_CONSUMED" in agg["frontier_live_quorum_blocked_reasons"]


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
    assert receipt["process_start_time"]
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

BACKEND = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")
UI = (ROOT / "frontend" / "src" / "components" / "helm" / "topdown" / "HelmCouncilView.tsx").read_text(
    encoding="utf-8")


def test_22_no_ui_field_maps_package_readiness_to_quorum_readiness():
    # The eight gates are surfaced as SEPARATE, independently-sourced fields.
    for gate in ("h1_package_state", "h1_package_integrity", "h1_credential_state",
                 "h1_founder_authorization", "h1_live_provider_proof",
                 "h1_frontier_live_quorum", "h1_promotion", "h1_safe_to_execute"):
        assert gate in BACKEND, f"backend does not expose separate gate '{gate}'"
        assert gate in UI, f"UI does not render separate gate '{gate}'"

    # Package readiness must never be the SOURCE of quorum/promotion/safe-to-execute.
    assert '"h1_frontier_live_quorum": "BLOCKED"' in BACKEND
    assert '"h1_promotion": "LOCKED"' in BACKEND
    assert '"h1_safe_to_execute": "NO"' in BACKEND
    # and the generic merged badge is gone
    assert "READY_FOR_FOUNDER_REVIEW" not in UI


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
    frontier_seat = {"member_id": "chatgpt", "adapter": "openai", "provider": "openai",
                     "requested_model": "gpt-5.6-terra", "endpoint": "https://api.openai.com/v1",
                     "timeout_seconds": 5, "schema_version": "1.0", "role": "reviewer"}
    _text, _resolved, _raw, meta = adapters.dispatch_ex(
        frontier_seat, "RUN ID: R1\nprompt", key="unused")
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
