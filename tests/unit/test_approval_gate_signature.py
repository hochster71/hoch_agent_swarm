"""Gate wiring tests: record_decision must fail closed without a founder signature."""
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend.approval_gate import ApprovalGate
from backend.mission_control import founder_signer


@pytest.fixture()
def gate(tmp_path):
    return ApprovalGate(base_dir=tmp_path)


@pytest.fixture()
def founder_key(tmp_path, monkeypatch):
    key = tmp_path / "fk"
    subprocess.run(["ssh-keygen", "-t", "ed25519", "-N", "", "-q",
                    "-C", "founder@hoch-has", "-f", str(key)], check=True)
    t, b, _ = (tmp_path / "fk.pub").read_text().split()
    signers = tmp_path / "allowed_signers"
    signers.write_text(f'founder@hoch-has namespaces="has-approval" {t} {b}\n')
    monkeypatch.setattr(founder_signer, "ALLOWED_SIGNERS", signers)
    return key


def _pending(gate):
    return gate.create_request("deploy epic fury to production",
                               {"risk_level": "HIGH", "mission_type": "RELEASE"})


def test_unsigned_approve_refused(gate, founder_key):
    app = _pending(gate)
    with pytest.raises(ValueError, match="founder signature"):
        gate.record_decision(app["approval_id"], "APPROVED")
    assert gate.load_queue()[0]["status"] == "PENDING" or \
        gate.load_queue()[0].get("founder_verified") is not True


def test_forged_signature_refused(gate, founder_key, tmp_path):
    app = _pending(gate)
    rogue = tmp_path / "rogue"
    subprocess.run(["ssh-keygen", "-t", "ed25519", "-N", "", "-q", "-f", str(rogue)], check=True)
    ts = datetime.now(timezone.utc).isoformat()
    sig = founder_signer.sign_approval({**app, "status": "APPROVED", "decision_at": ts}, rogue)
    with pytest.raises(ValueError):
        gate.record_decision(app["approval_id"], "APPROVED",
                             founder_signature=sig, founder_decision_at=ts)


def test_valid_founder_signature_accepted(gate, founder_key):
    app = _pending(gate)
    ts = datetime.now(timezone.utc).isoformat()
    sig = founder_signer.sign_approval(
        {**app, "status": "APPROVED", "decision_at": ts, "decision_note": None}, founder_key)
    result = gate.record_decision(app["approval_id"], "APPROVED",
                                  founder_signature=sig, founder_decision_at=ts)
    assert result["founder_verified"] is True


def test_reject_needs_no_signature(gate, founder_key):
    app = _pending(gate)
    result = gate.record_decision(app["approval_id"], "DENIED", note="not now")
    assert result["status"] == "DENIED"


def test_release_authority_freshness(founder_key):
    ok, reason = founder_signer.verify_release_authority(
        "packet-x", "2020-01-01T00:00:00+00:00", "bogus")
    assert not ok and "expired" in reason


def test_release_authority_roundtrip(founder_key):
    ts = datetime.now(timezone.utc).isoformat()
    payload = founder_signer.release_authority_payload("packet-x", ts)
    sig = founder_signer.sign_approval(payload, founder_key)
    ok, reason = founder_signer.verify_release_authority("packet-x", ts, sig)
    assert ok, reason
    ok2, _ = founder_signer.verify_release_authority("packet-OTHER", ts, sig)
    assert not ok2  # signature bound to the packet id
