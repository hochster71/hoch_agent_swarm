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
                    allowed_signers: Path = ALLOWED_SIGNERS) -> bool:
    """Fail-closed verification. True only if the signature is valid for the
    canonical payload under the committed founder public key."""
    try:
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
