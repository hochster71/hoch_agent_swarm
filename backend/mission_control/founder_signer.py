"""Founder approval signing/verification (C2 remediation).

Design: OpenSSH lightweight signatures (ssh-keygen -Y, OpenSSH >= 8.2).
- Private Ed25519 key: ~/.has_founder/founder_signing_key (passphrase-protected,
  outside the repo/agent workspace). Signing therefore requires the founder's
  passphrase — an interactive human factor agents do not possess.
- Public key: config/founder_allowed_signers (committed; agents verify only).
- Namespace "has-approval" prevents cross-protocol signature reuse.

Gates must treat any approval WITHOUT a valid signature as PENDING/FAIL_CLOSED.
"""
import json
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ALLOWED_SIGNERS = REPO_ROOT / "config" / "founder_allowed_signers"
NAMESPACE = "has-approval"
IDENTITY = "founder@hoch-has"
SIGNING_FIELDS = ("approval_id", "task_description", "risk_level", "status", "decision_at")


def canonical_payload(approval: dict) -> bytes:
    """Deterministic byte payload over the fields that carry authority."""
    subset = {k: approval.get(k) for k in SIGNING_FIELDS}
    return json.dumps(subset, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_approval(approval: dict, key_path: Path) -> str:
    """Sign an approval. Interactive (ssh-keygen prompts for the passphrase).
    Returns the armored SSH signature text."""
    with tempfile.TemporaryDirectory() as td:
        payload = Path(td) / "payload"
        payload.write_bytes(canonical_payload(approval))
        subprocess.run(
            ["ssh-keygen", "-Y", "sign", "-f", str(key_path), "-n", NAMESPACE, str(payload)],
            check=True,
        )
        return (Path(td) / "payload.sig").read_text(encoding="utf-8")


def verify_approval(approval: dict, signature: str,
                    allowed_signers: Path = None) -> bool:
    """Fail-closed verification. True only if the signature is valid for the
    canonical payload under the committed founder public key."""
    try:
        if allowed_signers is None:
            allowed_signers = ALLOWED_SIGNERS
        if not allowed_signers.exists():
            return False
        with tempfile.TemporaryDirectory() as td:
            sig = Path(td) / "payload.sig"
            sig.write_text(signature, encoding="utf-8")
            proc = subprocess.run(
                ["ssh-keygen", "-Y", "verify", "-f", str(allowed_signers),
                 "-I", IDENTITY, "-n", NAMESPACE, "-s", str(sig)],
                input=canonical_payload(approval),
                capture_output=True,
            )
            return proc.returncode == 0
    except Exception:
        return False


def approval_is_authorized(approval: dict) -> bool:
    """Single gate-facing check: APPROVED status + valid founder signature."""
    return (
        approval.get("status") == "APPROVED"
        and isinstance(approval.get("founder_signature"), str)
        and verify_approval(approval, approval["founder_signature"])
    )


# --- Release authority (C2: unauthenticated token minting remediation) ------
RELEASE_FRESHNESS_SECONDS = 600  # signed grants are valid for 10 minutes


def release_authority_payload(candidate_packet_id: str, decision_at: str) -> dict:
    """Canonical approval-shaped payload for a release-authority grant."""
    return {
        "approval_id": f"release:{candidate_packet_id}",
        "task_description": "grant formal release authority",
        "risk_level": "CRITICAL",
        "status": "APPROVED",
        "decision_at": decision_at,
    }


def verify_release_authority(candidate_packet_id: str, decision_at: str,
                             signature: str,
                             allowed_signers: Path = None) -> tuple[bool, str]:
    """Fail-closed check for minting release-authority tokens.

    Valid only if (a) the founder signature verifies over the canonical
    release payload and (b) the signed decision_at is fresh (anti-replay
    window of RELEASE_FRESHNESS_SECONDS).
    Returns (ok, reason).
    """
    from datetime import datetime, timezone
    try:
        signed = datetime.fromisoformat(str(decision_at).replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - signed).total_seconds()
    except Exception:
        return False, "invalid decision_at timestamp"
    if age < -60:
        return False, "decision_at is in the future"
    if age > RELEASE_FRESHNESS_SECONDS:
        return False, f"signed grant expired ({int(age)}s old > {RELEASE_FRESHNESS_SECONDS}s window)"
    payload = release_authority_payload(candidate_packet_id, decision_at)
    if not verify_approval(payload, signature, allowed_signers=allowed_signers):
        return False, "founder signature invalid for this packet/timestamp"
    return True, "verified"
