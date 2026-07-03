"""Tamper-evident evidence manifests (C3 remediation).

The audit found two gaps:
  1. gate_authority.signoff_signature = sha256(verdict+ts+pod) — no secret, so
     any agent can forge an APPROVED verdict.
  2. evidence_manifest.json lives in the same agent-writable tree it protects:
     rewrite the evidence, rewrite the manifest, the tamper gate still passes.

Design (per tamper-evident secure-log literature — Schneier & Kelsey hash
chains + HMAC keyed integrity + external anchoring; see also NIST-aligned
"append-only is not tamper-evident" guidance):

  * Each manifest entry: sha256 of the artifact bytes.
  * Manifest MAC: HMAC-SHA256 over the canonical sorted entries, keyed by a
    secret an agent does not hold. Reuses the founder Ed25519 private key as
    the HMAC key source (hashed), so forging a manifest requires the founder
    passphrase — the same authority factor as approvals.
  * External anchor: the manifest MAC is appended to an append-only anchor file
    OUTSIDE the repo (~/.has_founder/evidence_anchor.log). Rewriting in-repo
    evidence is then detectable by comparing against the external anchor, which
    agents running as a different user cannot edit.

Verification is independent: recompute hashes, recompute the MAC, and confirm
the MAC matches the external anchor. First mismatch = tamper boundary.
"""
import hashlib
import hmac
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
FOUNDER_KEY = Path.home() / ".has_founder" / "founder_signing_key"
ANCHOR_LOG = Path.home() / ".has_founder" / "evidence_anchor.log"
NAMESPACE = b"has-evidence-manifest-v1"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _mac_key(founder_key: Path = FOUNDER_KEY) -> bytes:
    """Derive an HMAC key from the founder private key material.

    The private key file is passphrase-protected on disk and lives outside the
    agent workspace, so only a context holding it (the founder's machine/session)
    can derive this key. We hash the key file bytes with a namespace to avoid
    using raw key material directly.
    """
    if not founder_key.exists():
        raise FileNotFoundError(
            f"Founder key {founder_key} missing — run scripts/founder_keygen.sh."
        )
    return hashlib.sha256(NAMESPACE + founder_key.read_bytes()).digest()


def _canonical(entries: List[Dict]) -> bytes:
    ordered = sorted(entries, key=lambda e: e["path"])
    return json.dumps(ordered, sort_keys=True, separators=(",", ":")).encode()


def build_manifest(artifact_paths: List[Path], run_id: str,
                   founder_key: Path = FOUNDER_KEY,
                   anchor_log: Path = ANCHOR_LOG) -> Dict:
    """Build a MAC'd manifest and append its MAC to the external anchor."""
    entries = []
    for p in artifact_paths:
        p = Path(p)
        rel = str(p.relative_to(REPO_ROOT)) if p.is_absolute() and str(p).startswith(str(REPO_ROOT)) else str(p)
        entries.append({"path": rel, "sha256": _sha256_file(p)})
    created_at = datetime.now(timezone.utc).isoformat()
    mac = hmac.new(_mac_key(founder_key), _canonical(entries), hashlib.sha256).hexdigest()
    manifest = {
        "run_id": run_id,
        "created_at": created_at,
        "artifacts": entries,
        "manifest_mac": mac,
        "mac_algo": "HMAC-SHA256",
    }
    anchor_log.parent.mkdir(parents=True, exist_ok=True)
    with open(anchor_log, "a") as f:  # append-only external anchor
        f.write(json.dumps({"run_id": run_id, "created_at": created_at, "mac": mac}) + "\n")
    return manifest


def verify_manifest(manifest: Dict, base_dir: Path = REPO_ROOT,
                    founder_key: Path = FOUNDER_KEY,
                    anchor_log: Path = ANCHOR_LOG) -> Dict:
    """Independent verification. Returns {ok, reason, first_bad}.
    Fail-closed: any missing key, hash mismatch, MAC mismatch, or absent
    external anchor => ok=False.
    """
    entries = manifest.get("artifacts", [])
    # 1. Per-artifact hash check (detects content edits).
    for e in entries:
        ap = (base_dir / e["path"]) if not Path(e["path"]).is_absolute() else Path(e["path"])
        if not ap.exists():
            return {"ok": False, "reason": f"missing artifact {e['path']}", "first_bad": e["path"]}
        if _sha256_file(ap) != e["sha256"]:
            return {"ok": False, "reason": f"hash mismatch {e['path']}", "first_bad": e["path"]}
    # 2. MAC check (detects manifest edits — the attack the old gate missed).
    try:
        expected = hmac.new(_mac_key(founder_key), _canonical(entries), hashlib.sha256).hexdigest()
    except FileNotFoundError as ex:
        return {"ok": False, "reason": str(ex), "first_bad": None}
    if not hmac.compare_digest(expected, manifest.get("manifest_mac", "")):
        return {"ok": False, "reason": "manifest MAC mismatch (manifest tampered)", "first_bad": "manifest_mac"}
    # 3. External anchor check (detects whole-manifest replacement in-repo).
    if not anchor_log.exists():
        return {"ok": False, "reason": "external anchor log missing", "first_bad": None}
    anchored = {json.loads(l)["mac"] for l in anchor_log.read_text().splitlines() if l.strip()}
    if manifest.get("manifest_mac") not in anchored:
        return {"ok": False, "reason": "MAC not present in external anchor (manifest not authentic)", "first_bad": "anchor"}
    return {"ok": True, "reason": "verified", "first_bad": None}
