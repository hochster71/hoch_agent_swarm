"""Roundtrip + forgery tests for founder approval signatures (C2/C3 remediation)."""
import subprocess
from pathlib import Path

import pytest

from backend.mission_control.founder_signer import (
    canonical_payload, sign_approval, verify_approval, approval_is_authorized)

APPROVAL = {
    "approval_id": "app-test0001",
    "task_description": "deploy epic fury to staging",
    "risk_level": "HIGH",
    "status": "APPROVED",
    "decision_at": "2026-07-02T21:00:00+00:00",
}


@pytest.fixture()
def keypair(tmp_path):
    key = tmp_path / "test_key"
    subprocess.run(["ssh-keygen", "-t", "ed25519", "-N", "", "-q",
                    "-C", "founder@hoch-has", "-f", str(key)], check=True)
    pub = (tmp_path / "test_key.pub").read_text().strip()
    parts = pub.split()  # type blob comment
    signers = tmp_path / "allowed_signers"
    signers.write_text(f'founder@hoch-has namespaces="has-approval" {parts[0]} {parts[1]}\n')
    return key, signers


def test_sign_verify_roundtrip(keypair):
    key, signers = keypair
    sig = sign_approval(APPROVAL, key)
    assert verify_approval(APPROVAL, sig, allowed_signers=signers)


def test_tampered_payload_rejected(keypair):
    key, signers = keypair
    sig = sign_approval(APPROVAL, key)
    forged = dict(APPROVAL, task_description="transfer stripe balance out")
    assert not verify_approval(forged, sig, allowed_signers=signers)


def test_status_flip_rejected(keypair):
    """The exact attack from the audit: agent flips PENDING->APPROVED."""
    key, signers = keypair
    pending = dict(APPROVAL, status="PENDING")
    sig = sign_approval(pending, key)
    flipped = dict(pending, status="APPROVED", founder_signature=sig)
    assert not verify_approval(flipped, sig, allowed_signers=signers)


def test_unsigned_approval_not_authorized():
    assert not approval_is_authorized(dict(APPROVAL))  # no signature -> fail closed


def test_wrong_key_rejected(keypair, tmp_path):
    _, signers = keypair
    rogue = tmp_path / "rogue_key"
    subprocess.run(["ssh-keygen", "-t", "ed25519", "-N", "", "-q",
                    "-C", "agent@rogue", "-f", str(rogue)], check=True)
    sig = sign_approval(APPROVAL, rogue)
    assert not verify_approval(APPROVAL, sig, allowed_signers=signers)


def test_canonical_payload_deterministic():
    assert canonical_payload(dict(APPROVAL)) == canonical_payload(
        dict(reversed(list(APPROVAL.items()))))
