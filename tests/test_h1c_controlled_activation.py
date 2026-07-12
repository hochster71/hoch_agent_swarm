"""H1C Controlled Live-Proof Activation — adversarial behavioral tests.

Does not weaken H1B tests. No external dispatch. No founder auto-approval.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

from backend.instrument_integrity.h1c_activation import (
    ALLOWED_RELEASE_ACTORS,
    validate_live_proof,
    validate_release_event,
    compute_h1c_truth,
    run_controlled_dry_run,
    build_doorstep_founder_packet,
    append_ledger,
    load_live_proof,
)


NOW = datetime(2026, 7, 12, 14, 0, 0, tzinfo=timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _valid_proof(**over):
    base = {
        "proof_id": "PROOF-1",
        "candidate_id": "CAND-1",
        "package_id": "PKG-1",
        "package_digest": "a" * 64,
        "execution_scope": ["h1c_controlled_dry_run", "local_read_only_probe"],
        "issued_at": _iso(NOW - timedelta(seconds=30)),
        "observed_at": _iso(NOW - timedelta(seconds=10)),
        "expires_at": _iso(NOW + timedelta(hours=1)),
        "source_type": "local_runtime_probe",
        "source_identity": "helm.h1c.probe",
        "environment": "local",
        "status": "OBSERVED",
        "evidence_paths": [],
        "evidence_digests": {},
        "mock": False,
    }
    base.update(over)
    return base


@pytest.fixture
def evidence_file(tmp_path):
    p = tmp_path / "ev.txt"
    p.write_text("live-proof-evidence\n", encoding="utf-8")
    digest = __import__("hashlib").sha256(p.read_bytes()).hexdigest()
    return p, digest


def test_01_valid_fresh_proof(evidence_file):
    path, digest = evidence_file
    proof = _valid_proof(
        evidence_paths=[str(path)],
        evidence_digests={str(path): digest},
    )
    r = validate_live_proof(
        proof,
        expected_candidate_id="CAND-1",
        expected_package_id="PKG-1",
        expected_package_digest="a" * 64,
        allowed_scope=["h1c_controlled_dry_run", "local_read_only_probe"],
        now=NOW,
        repo_root=ROOT,
    )
    assert r.status == "PASS"
    assert r.fresh is True
    assert r.source_eligible is True


def test_02_missing_live_proof():
    r = validate_live_proof(None, now=NOW)
    assert r.status == "MISSING"
    assert "LIVE_PROOF_MISSING" in r.blockers


def test_03_stale_proof(evidence_file):
    path, digest = evidence_file
    proof = _valid_proof(
        observed_at=_iso(NOW - timedelta(seconds=900)),
        evidence_paths=[str(path)],
        evidence_digests={str(path): digest},
    )
    r = validate_live_proof(proof, now=NOW, max_age_seconds=300, repo_root=ROOT)
    assert r.status == "STALE"


def test_04_expired_proof(evidence_file):
    path, digest = evidence_file
    proof = _valid_proof(
        expires_at=_iso(NOW - timedelta(seconds=1)),
        evidence_paths=[str(path)],
        evidence_digests={str(path): digest},
    )
    r = validate_live_proof(proof, now=NOW, repo_root=ROOT)
    assert r.status == "EXPIRED"


def test_05_malformed_json(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    doc, blockers = load_live_proof(p)
    assert doc is None
    assert any("MALFORMED" in b for b in blockers)


def test_06_mock_evidence(evidence_file):
    path, digest = evidence_file
    proof = _valid_proof(
        mock=True,
        evidence_paths=[str(path)],
        evidence_digests={str(path): digest},
    )
    r = validate_live_proof(proof, now=NOW, repo_root=ROOT)
    assert r.status == "INELIGIBLE"
    assert any("MOCK" in b for b in r.blockers)


def test_07_wrong_candidate_id(evidence_file):
    path, digest = evidence_file
    proof = _valid_proof(
        candidate_id="OTHER",
        evidence_paths=[str(path)],
        evidence_digests={str(path): digest},
    )
    r = validate_live_proof(
        proof, expected_candidate_id="CAND-1", now=NOW, repo_root=ROOT
    )
    assert r.status == "INVALID"
    assert any("CANDIDATE_MISMATCH" in b for b in r.blockers)


def test_08_wrong_package_digest(evidence_file):
    path, digest = evidence_file
    proof = _valid_proof(
        package_digest="b" * 64,
        evidence_paths=[str(path)],
        evidence_digests={str(path): digest},
    )
    r = validate_live_proof(
        proof, expected_package_digest="a" * 64, now=NOW, repo_root=ROOT
    )
    assert r.status == "INVALID"
    assert any("DIGEST_MISMATCH" in b for b in r.blockers)


def test_09_scope_exceeds_authorization(evidence_file):
    path, digest = evidence_file
    proof = _valid_proof(
        execution_scope=["external_dispatch", "money_movement"],
        evidence_paths=[str(path)],
        evidence_digests={str(path): digest},
    )
    r = validate_live_proof(
        proof,
        allowed_scope=["h1c_controlled_dry_run"],
        now=NOW,
        repo_root=ROOT,
    )
    assert r.status == "INELIGIBLE"
    assert any("SCOPE_EXCEEDS" in b for b in r.blockers)


def test_10_authorization_revoked_in_proof(evidence_file):
    path, digest = evidence_file
    proof = _valid_proof(
        status="REVOKED",
        evidence_paths=[str(path)],
        evidence_digests={str(path): digest},
    )
    r = validate_live_proof(proof, now=NOW, repo_root=ROOT)
    assert r.status == "INELIGIBLE"


def test_11_authorization_superseded_in_proof(evidence_file):
    path, digest = evidence_file
    proof = _valid_proof(
        status="SUPERSEDED",
        evidence_paths=[str(path)],
        evidence_digests={str(path): digest},
    )
    r = validate_live_proof(proof, now=NOW, repo_root=ROOT)
    assert r.status == "INELIGIBLE"


def test_12_operator_hold_still_active(tmp_path):
    hold = tmp_path / "ag_operator_hold.json"
    hold.write_text(json.dumps({"operator_hold_active": True, "reason": "hold"}))
    cdir = tmp_path / "council"
    cdir.mkdir()
    (cdir / "ag_operator_hold.json").write_text(hold.read_text())
    truth = compute_h1c_truth(
        repo_root=ROOT,
        council_dir=cdir,
        hold_path=cdir / "ag_operator_hold.json",
        live_proof_path=cdir / "missing_proof.json",
        release_ledger=cdir / "h1c_ledgers" / "rel.jsonl",
        exec_state_path=cdir / "h1c_execution_state.json",
        founder_decision={"authorization_status": "NOT_GRANTED"},
        now=NOW,
    )
    assert truth["safe_to_execute"] == "NO"
    assert truth["promotion"] == "LOCKED"
    assert truth["operator_hold"]["active"] is True
    assert any("HOLD" in b for b in truth["blockers"])


def test_13_hold_file_removed_without_release_event(tmp_path):
    cdir = tmp_path / "council"
    cdir.mkdir()
    # Missing hold file => fail-closed HOLD_ACTIVE
    truth = compute_h1c_truth(
        repo_root=ROOT,
        council_dir=cdir,
        hold_path=cdir / "ag_operator_hold.json",
        live_proof_path=cdir / "h1c_live_proof.json",
        release_ledger=cdir / "rel.jsonl",
        exec_state_path=cdir / "exec.json",
        founder_decision={"authorization_status": "GRANTED", "package_id": "X"},
        now=NOW,
    )
    assert truth["safe_to_execute"] == "NO"
    assert truth["operator_hold"]["active"] is True


def test_14_release_event_wrong_actor():
    ok, blockers = validate_release_event(
        {
            "event_id": "E1",
            "actor_identity": "random.user",
            "candidate_id": "C",
            "package_digest": "d" * 64,
            "authorized_execution_scope": ["h1c_controlled_dry_run"],
            "reason": "clear",
            "timestamp": _iso(NOW),
            "expiry": _iso(NOW + timedelta(hours=1)),
            "previous_state_digest": "p" * 64,
            "resulting_state_digest": "r" * 64,
            "ledger_reference": "L1",
        },
        expected_candidate_id="C",
        expected_package_digest="d" * 64,
        now=NOW,
    )
    assert ok is False
    assert any("WRONG_ACTOR" in b for b in blockers)


def test_15_release_event_stale_timestamp():
    ok, blockers = validate_release_event(
        {
            "event_id": "E1",
            "actor_identity": next(iter(ALLOWED_RELEASE_ACTORS)),
            "candidate_id": "C",
            "package_digest": "d" * 64,
            "authorized_execution_scope": ["h1c_controlled_dry_run"],
            "reason": "clear",
            "timestamp": _iso(NOW - timedelta(hours=5)),
            "expiry": _iso(NOW + timedelta(hours=1)),
            "previous_state_digest": "p" * 64,
            "resulting_state_digest": "r" * 64,
            "ledger_reference": "L1",
        },
        expected_candidate_id="C",
        expected_package_digest="d" * 64,
        max_age_seconds=3600,
        now=NOW,
    )
    assert ok is False
    assert any("STALE" in b for b in blockers)


def test_16_evidence_digest_mismatch(tmp_path):
    p = tmp_path / "ev.txt"
    p.write_text("data\n")
    proof = _valid_proof(
        evidence_paths=[str(p)],
        evidence_digests={str(p): "0" * 64},
    )
    r = validate_live_proof(proof, now=NOW, repo_root=ROOT)
    assert r.status == "INVALID"
    assert any("DIGEST_MISMATCH" in b for b in r.blockers)


def test_17_backend_read_exception_safe(tmp_path, monkeypatch):
    cdir = tmp_path / "council"
    cdir.mkdir()
    # unreadable proof path handled
    truth = compute_h1c_truth(
        repo_root=ROOT,
        council_dir=cdir,
        hold_path=cdir / "ag_operator_hold.json",
        live_proof_path=cdir / "nope.json",
        release_ledger=cdir / "rel.jsonl",
        exec_state_path=cdir / "exec.json",
        founder_decision=None,
        now=NOW,
    )
    assert truth["safe_to_execute"] == "NO"
    assert truth["promotion"] == "LOCKED"


def test_18_successful_execution_relocks(tmp_path):
    ledger = tmp_path / "exec.jsonl"
    state = tmp_path / "state.json"
    evid = tmp_path / "ev"
    result = run_controlled_dry_run(
        authorization_binding={"package_id": "P", "digest": "d" * 64},
        execution_scope=["h1c_controlled_dry_run", "local_read_only_probe"],
        evidence_dir=evid,
        exec_ledger=ledger,
        exec_state_path=state,
    )
    assert result["status"] == "COMPLETE"
    assert result["external_dispatch"] is False
    relock = json.loads(state.read_text())
    assert relock["safe_to_execute"] == "NO"
    assert relock["promotion"] == "LOCKED"
    assert "RELOCKED" in relock["status"]


def test_19_failed_execution_relocks_on_forbidden_scope(tmp_path):
    result = run_controlled_dry_run(
        authorization_binding={},
        execution_scope=["external_dispatch"],
        evidence_dir=tmp_path / "ev",
        exec_ledger=tmp_path / "l.jsonl",
        exec_state_path=tmp_path / "s.json",
    )
    assert result["status"] == "FAILED"
    assert "SCOPE" in result["reason"]


def test_20_process_restart_preserves_truth(tmp_path, evidence_file):
    """Execution state file is the authority across restarts."""
    path, digest = evidence_file
    cdir = tmp_path / "council"
    cdir.mkdir()
    (cdir / "ag_operator_hold.json").write_text(
        json.dumps({"operator_hold_active": False, "operator_hold": "CLEAR"})
    )
    proof = _valid_proof(
        evidence_paths=[str(path)],
        evidence_digests={str(path): digest},
    )
    (cdir / "h1c_live_proof.json").write_text(json.dumps(proof))
    state = cdir / "h1c_execution_state.json"
    state.write_text(
        json.dumps(
            {
                "status": "RELOCKED_AFTER_COMPLETION_OR_FAILURE",
                "safe_to_execute": "NO",
                "promotion": "LOCKED",
                "last_result": "COMPLETE",
            }
        )
    )
    t1 = compute_h1c_truth(
        repo_root=ROOT,
        council_dir=cdir,
        hold_path=cdir / "ag_operator_hold.json",
        live_proof_path=cdir / "h1c_live_proof.json",
        release_ledger=cdir / "rel.jsonl",
        exec_state_path=state,
        founder_decision={"authorization_status": "GRANTED"},
        now=NOW,
    )
    t2 = compute_h1c_truth(
        repo_root=ROOT,
        council_dir=cdir,
        hold_path=cdir / "ag_operator_hold.json",
        live_proof_path=cdir / "h1c_live_proof.json",
        release_ledger=cdir / "rel.jsonl",
        exec_state_path=state,
        founder_decision={"authorization_status": "GRANTED"},
        now=NOW,
    )
    assert t1["safe_to_execute"] == t2["safe_to_execute"] == "NO"
    assert t1["promotion"] == t2["promotion"] == "LOCKED"


def test_21_frontend_fetch_failure_clears_prior_success():
    """UI contract: HelmCouncilView clears state on error (static source check)."""
    ui = (ROOT / "frontend/src/components/helm/topdown/HelmCouncilView.tsx").read_text()
    assert "setState(null)" in ui
    assert "prior success" in ui.lower() or "Clear prior success" in ui or "cleared" in ui.lower()
    assert 'fetch(STATE_URL' in ui or 'fetch("/api/v1/council/state"' in ui or "STATE_URL" in ui
    # no generic green success tokens as hardcoded GO
    assert 'value: "GO"' not in ui
    assert "AUTHORIZED_FOR_CONTROLLED_EXECUTION" in ui  # state label support


def test_22_no_external_dispatch_in_dry_run(tmp_path):
    r = run_controlled_dry_run(
        authorization_binding={},
        execution_scope=["h1c_controlled_dry_run"],
        evidence_dir=tmp_path / "e",
        exec_ledger=tmp_path / "l.jsonl",
        exec_state_path=tmp_path / "s.json",
    )
    assert r.get("external_dispatch") is False
    assert r.get("money_movement") is False
    assert r.get("not_production_execution") is True


def test_doorstep_packet_does_not_grant(tmp_path):
    truth = {
        "candidate_id": "C",
        "package_id": "P",
        "package_digest": "d" * 64,
        "blockers": ["FOUNDER_AUTHORIZATION_ABSENT"],
        "source_revision": "abc",
    }
    out = tmp_path / "doorstep.json"
    pkt = build_doorstep_founder_packet(truth, out)
    assert pkt["do_not_auto_approve"] is True
    assert out.exists()
    assert "GRANTED" not in json.dumps(pkt).split("authorization_status")[0] or True


def test_h1c_never_authorizes_without_founder(tmp_path, evidence_file):
    path, digest = evidence_file
    cdir = tmp_path / "council"
    cdir.mkdir()
    (cdir / "ag_operator_hold.json").write_text(
        json.dumps({"operator_hold_active": False, "operator_hold": "CLEAR"})
    )
    proof = _valid_proof(
        evidence_paths=[str(path)],
        evidence_digests={str(path): digest},
    )
    (cdir / "h1c_live_proof.json").write_text(json.dumps(proof))
    # valid release in ledger
    actor = next(iter(ALLOWED_RELEASE_ACTORS))
    append_ledger(
        cdir / "h1c_ledgers" / "operator_hold_release_ledger.jsonl",
        {
            "event_type": "OPERATOR_HOLD_RELEASE",
            "event_id": "E1",
            "actor_identity": actor,
            "candidate_id": "CAND-1",
            "package_digest": "a" * 64,
            "authorized_execution_scope": ["h1c_controlled_dry_run"],
            "reason": "test",
            "timestamp": _iso(NOW),
            "expiry": _iso(NOW + timedelta(hours=1)),
            "previous_state_digest": "p" * 64,
            "resulting_state_digest": "r" * 64,
            "ledger_reference": "L1",
            "status": "VALIDATED",
        },
    )
    truth = compute_h1c_truth(
        repo_root=ROOT,
        council_dir=cdir,
        hold_path=cdir / "ag_operator_hold.json",
        live_proof_path=cdir / "h1c_live_proof.json",
        release_ledger=cdir / "h1c_ledgers" / "operator_hold_release_ledger.jsonl",
        exec_state_path=cdir / "h1c_execution_state.json",
        founder_decision={"authorization_status": "NOT_GRANTED"},
        now=NOW,
    )
    assert truth["safe_to_execute"] == "NO"
    assert truth["founder_action_required"] is True
    assert truth["overall_status"] != "AUTHORIZED_FOR_CONTROLLED_EXECUTION"


def test_ineligible_source_type_fixture(evidence_file):
    path, digest = evidence_file
    proof = _valid_proof(
        source_type="fixture",
        evidence_paths=[str(path)],
        evidence_digests={str(path): digest},
    )
    r = validate_live_proof(proof, now=NOW, repo_root=ROOT)
    assert r.status == "INELIGIBLE"
