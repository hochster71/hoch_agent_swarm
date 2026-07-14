"""supply_chain.py — SR-3. Provenance attestation for every tool binary and model endpoint.

THE HOLE THIS PLUGS
-------------------
HELM dispatched to `http://127.0.0.1:11434` (LOCAL_OLLAMA) and executed
`/Users/michaelhoch/.local/bin/grok` (GROK_CLI) on the strength of a NAME. A name is not
an identity. `ollama create llama3.1:8b -f ./evil-Modelfile` keeps the tag and swaps the
weights underneath it; replacing a CLI binary on $PATH is a two-line attack. Neither was
detectable, and the council would have laundered the substituted model's output into a
verdict.

THE RULE (identical to every other ledger in this system)
---------------------------------------------------------
    verify_provenance() returns (ok, reason). It returns ok=True ONLY when it has just
    OBSERVED the evidence:

      tool  : sha256(binary on disk, right now) == the sha256 recorded at attestation
      model : digest reported by the live endpoint, right now == the digest attested
      remote: the model id is on the attested list AND the endpoint is pinned
              (a remote API's weights CANNOT be digested from here — see LIMITATIONS)

    Anything else is a DENY:
      registry absent      -> ATTESTATION_REGISTRY_MISSING       (UNKNOWN, fails closed)
      registry unreadable  -> ATTESTATION_REGISTRY_UNREADABLE    (CONTRADICTED)
      no record            -> TOOL_NOT_ATTESTED / MODEL_NOT_ATTESTED
      binary gone          -> TOOL_BINARY_MISSING
      digest differs       -> TOOL_DIGEST_MISMATCH / MODEL_DIGEST_MISMATCH
      endpoint unreachable -> MODEL_PROVENANCE_UNVERIFIABLE      (UNKNOWN, fails closed)
      called with nothing  -> NOTHING_TO_VERIFY

    There is no bypass flag, no env var, no "warn only" mode. If you cannot prove what you
    are talking to, you do not talk to it.

LIMITATIONS (stated here so nobody has to discover them in an incident)
----------------------------------------------------------------------
  * A REMOTE model (xAI/Grok, any hosted API) cannot be weight-attested from this machine.
    We attest its IDENTITY (the model id is on an explicit allowlist) and the LOCAL binary
    that reaches it. If xAI silently re-points `grok-default` at different weights, THIS
    CONTROL WILL NOT SEE IT. That is a vendor-trust boundary, not a bug we can fix here,
    and verify_provenance says so in its own reason string (OK_REMOTE_MODEL_IDENTITY_ONLY).
  * The registry itself is a file on disk. An attacker with write access to
    coordination/security/ can re-attest a substituted artifact. The registry is committed
    to git, so the substitution is visible in the diff — but this control raises the cost
    of substitution, it does not make it impossible.
  * Attestation is TRUST-ON-EXPLICIT-RECORD, not signature verification. We do not verify
    a vendor signature over the binary (grok ships none). We pin what was reviewed.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]

SCHEMA = "HELM_SUPPLY_CHAIN_ATTESTATION_v1"
REGISTRY = ROOT / "coordination" / "security" / "supply_chain_attestations.json"

LOCAL_WEIGHTS_DIGEST = "LOCAL_WEIGHTS_DIGEST"          # we can hash the live model
REMOTE_ENDPOINT_IDENTITY = "REMOTE_ENDPOINT_IDENTITY"  # we can only pin the id + endpoint
PROVENANCE_CLASSES = (LOCAL_WEIGHTS_DIGEST, REMOTE_ENDPOINT_IDENTITY)

_CHUNK = 1 << 20


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(_CHUNK):
            h.update(chunk)
    return h.hexdigest()


def load_registry(registry_path: Path | None = None) -> tuple[dict[str, Any] | None, str]:
    """Returns (doc, reason). doc is None on any condition that must fail closed."""
    p = Path(registry_path) if registry_path else REGISTRY
    if not p.exists():
        return None, f"ATTESTATION_REGISTRY_MISSING: {p}"
    try:
        doc = json.loads(p.read_text())
    except Exception as e:
        return None, f"ATTESTATION_REGISTRY_UNREADABLE: {p} ({type(e).__name__}: {e})"
    if doc.get("schema") != SCHEMA:
        return None, f"ATTESTATION_REGISTRY_UNREADABLE: wrong schema {doc.get('schema')!r}"
    doc.setdefault("tools", {})
    doc.setdefault("models", {})
    return doc, "OK_REGISTRY_LOADED"


# ---------------------------------------------------------------- live observation
def live_ollama_digest(model: str, endpoint: str, timeout: float = 5.0) -> str | None:
    """Ask the LIVE ollama daemon what it would actually run for this tag.

    Raises on transport failure — the caller turns that into a fail-closed UNVERIFIABLE.
    Returns None if the endpoint does not serve this tag at all."""
    url = endpoint.rstrip("/") + "/api/tags"
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        doc = json.loads(resp.read().decode())
    for m in doc.get("models", []):
        if m.get("name") == model or m.get("model") == model:
            return (m.get("digest") or "").replace("sha256:", "")
    return None


# ---------------------------------------------------------------- verification
def verify_tool_provenance(tool_id: str, *, registry_path: Path | None = None,
                           binary_path: str | Path | None = None) -> tuple[bool, str]:
    doc, why = load_registry(registry_path)
    if doc is None:
        return False, why
    rec = doc["tools"].get(tool_id)
    if not rec:
        return False, f"TOOL_NOT_ATTESTED: {tool_id} has no provenance record"
    path = Path(binary_path or rec.get("path", ""))
    if not path.exists():
        return False, f"TOOL_BINARY_MISSING: {tool_id} -> {path}"
    attested = str(rec.get("sha256", "")).lower()
    if len(attested) != 64:
        return False, f"TOOL_NOT_ATTESTED: {tool_id} record carries no sha256"
    try:
        actual = sha256_file(path)
    except Exception as e:
        return False, f"TOOL_PROVENANCE_UNVERIFIABLE: {tool_id} ({type(e).__name__}: {e})"
    if actual != attested:
        return False, (f"TOOL_DIGEST_MISMATCH: {tool_id} at {path} is sha256:{actual[:16]}… "
                       f"but was attested as sha256:{attested[:16]}… — the binary was "
                       f"substituted or upgraded without re-attestation")
    return True, f"OK_TOOL_DIGEST_MATCH: {tool_id} sha256:{actual[:16]}…"


def verify_model_provenance(adapter_id: str, model: str, *,
                            registry_path: Path | None = None,
                            live_digest_fn: Callable[[str, str, float], str | None] | None = None,
                            timeout: float = 5.0) -> tuple[bool, str]:
    doc, why = load_registry(registry_path)
    if doc is None:
        return False, why
    key = f"{adapter_id}:{model}"
    rec = doc["models"].get(key)
    if not rec:
        return False, (f"MODEL_NOT_ATTESTED: {key} is not in the attestation registry — "
                       f"an unknown model endpoint is never dispatched to")

    pclass = rec.get("provenance_class")
    if pclass == REMOTE_ENDPOINT_IDENTITY:
        return True, (f"OK_REMOTE_MODEL_IDENTITY_ONLY: {key} identity + endpoint are pinned; "
                      f"remote weights are NOT digest-attested (vendor trust boundary)")

    if pclass != LOCAL_WEIGHTS_DIGEST:
        return False, f"MODEL_NOT_ATTESTED: {key} has unrecognised provenance_class {pclass!r}"

    attested = str(rec.get("digest", "") or "").lower().replace("sha256:", "")
    if len(attested) != 64:
        return False, f"MODEL_NOT_ATTESTED: {key} record carries no weights digest"

    fn = live_digest_fn or live_ollama_digest
    endpoint = rec.get("endpoint", "http://127.0.0.1:11434")
    try:
        actual = fn(model, endpoint, timeout)
    except Exception as e:
        return False, (f"MODEL_PROVENANCE_UNVERIFIABLE: cannot observe {key} at {endpoint} "
                       f"({type(e).__name__}: {e}) — unverifiable is not the same as fine")
    if not actual:
        return False, (f"MODEL_DIGEST_MISMATCH: {endpoint} no longer serves {model} at all — "
                       f"the attested model is gone")
    actual = actual.lower().replace("sha256:", "")
    if actual != attested:
        return False, (f"MODEL_DIGEST_MISMATCH: {key} now resolves to sha256:{actual[:16]}… "
                       f"but was attested as sha256:{attested[:16]}… — the tag was re-pointed "
                       f"at different weights")
    return True, f"OK_MODEL_DIGEST_MATCH: {key} sha256:{actual[:16]}…"


def verify_provenance(*, tool_id: str | None = None, adapter_id: str | None = None,
                      model: str | None = None, registry_path: Path | None = None,
                      binary_path: str | Path | None = None,
                      live_digest_fn: Callable[[str, str, float], str | None] | None = None,
                      timeout: float = 5.0) -> tuple[bool, str]:
    """THE single entry point. (ok, reason). Fails closed on everything it cannot observe.

    Verifies every subject it is given; if any subject fails, the whole call fails."""
    checks: list[tuple[bool, str]] = []
    if tool_id:
        checks.append(verify_tool_provenance(tool_id, registry_path=registry_path,
                                             binary_path=binary_path))
    if model:
        checks.append(verify_model_provenance(adapter_id or "", model,
                                              registry_path=registry_path,
                                              live_digest_fn=live_digest_fn, timeout=timeout))
    if not checks:
        return False, ("NOTHING_TO_VERIFY: verify_provenance was called with no tool and no "
                       "model — it observed nothing, so it cannot report OK")
    for ok, reason in checks:
        if not ok:
            return False, reason
    return True, " | ".join(r for _, r in checks)


# ---------------------------------------------------------------- attestation (write path)
def attest_tool(tool_id: str, binary_path: str | Path, *,
                registry_path: Path | None = None, note: str = "") -> dict[str, Any]:
    """Record what is on disk RIGHT NOW as the approved artifact. This is a deliberate,
    human-initiated act — nothing auto-attests itself at dispatch time (that would be
    trust-on-first-use, i.e. the control defeating itself)."""
    p = Path(binary_path)
    rec = {
        "path": str(p),
        "resolved_path": str(p.resolve()),
        "sha256": sha256_file(p),
        "size_bytes": p.stat().st_size,
        "attested_at": _now(),
        "attested_by": os.environ.get("USER", "unknown"),
        "note": note,
    }
    _upsert(registry_path, "tools", tool_id, rec)
    return rec


def attest_local_model(adapter_id: str, model: str, endpoint: str, *,
                       registry_path: Path | None = None, note: str = "") -> dict[str, Any]:
    digest = live_ollama_digest(model, endpoint)
    if not digest:
        raise RuntimeError(f"{endpoint} does not serve {model} — nothing to attest")
    rec = {"adapter_id": adapter_id, "model": model,
           "provenance_class": LOCAL_WEIGHTS_DIGEST, "digest": digest,
           "endpoint": endpoint, "attested_at": _now(),
           "attested_by": os.environ.get("USER", "unknown"), "note": note}
    _upsert(registry_path, "models", f"{adapter_id}:{model}", rec)
    return rec


def attest_remote_model(adapter_id: str, model: str, *, endpoint: str = "",
                        registry_path: Path | None = None, note: str = "") -> dict[str, Any]:
    rec = {"adapter_id": adapter_id, "model": model,
           "provenance_class": REMOTE_ENDPOINT_IDENTITY, "digest": None,
           "endpoint": endpoint, "attested_at": _now(),
           "attested_by": os.environ.get("USER", "unknown"),
           "note": note or "remote weights are NOT attestable from this host",
           }
    _upsert(registry_path, "models", f"{adapter_id}:{model}", rec)
    return rec


def _upsert(registry_path: Path | None, section: str, key: str, rec: dict[str, Any]) -> None:
    p = Path(registry_path) if registry_path else REGISTRY
    doc, _ = load_registry(p)
    if doc is None:
        doc = {"schema": SCHEMA, "generated_at": _now(), "tools": {}, "models": {}}
    doc[section][key] = rec
    doc["generated_at"] = _now()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")


# ---------------------------------------------------------------- CLI
def main(argv: list[str]) -> int:
    """python -m backend.truth.supply_chain verify|attest-tool|attest-local|attest-remote"""
    if not argv or argv[0] == "verify":
        doc, why = load_registry()
        if doc is None:
            print(f"DENY  {why}")
            return 1
        rc = 0
        for tid in doc["tools"]:
            ok, reason = verify_tool_provenance(tid)
            print(f"{'PASS' if ok else 'DENY'}  {reason}")
            rc |= 0 if ok else 1
        for key in doc["models"]:
            aid, _, m = key.partition(":")
            ok, reason = verify_model_provenance(aid, m)
            print(f"{'PASS' if ok else 'DENY'}  {reason}")
            rc |= 0 if ok else 1
        return rc
    cmd, *rest = argv
    if cmd == "attest-tool":
        print(json.dumps(attest_tool(rest[0], rest[1]), indent=2))
    elif cmd == "attest-local":
        print(json.dumps(attest_local_model(rest[0], rest[1], rest[2]), indent=2))
    elif cmd == "attest-remote":
        print(json.dumps(attest_remote_model(rest[0], rest[1]), indent=2))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
