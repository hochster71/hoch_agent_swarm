"""Adversarial matrix for the A7-remediation composed extensions (council directive 2026-07-19).

Covers: extension/manifest absent, malformed proof payloads, proof-encoding conflicts
(fail closed, never merged), registry absence/malformation/under-attribution (fail closed
to constitutional fallback), dual-read containment (structural), and binding telemetry.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.helm_runtime.extensions import constitutional_gate as cg  # noqa: E402
from backend.helm_runtime.extensions import model_routing as mr  # noqa: E402


# ── gate fail-closed ───────────────────────────────────────────────────────────────
def test_gate_none_record_is_unknown_blocked():
    r = cg.govern_decision(None)
    assert r.governance_state == "UNKNOWN" and r.may_advance is False


def test_gate_malformed_record_is_unknown_blocked():
    for bad in ("a-string", 42, ["list"], b"bytes"):
        r = cg.govern_decision(bad)  # type: ignore[arg-type]
        assert r.may_advance is False


def test_gate_manifest_absent_fails_closed(monkeypatch):
    monkeypatch.setattr(cg, "_MANIFEST_AVAILABLE", False)
    r = cg.govern_decision({"evidence_class": "OBSERVED"})
    assert r.governance_state == "UNKNOWN" and r.may_advance is False
    assert "governance_manifest" in r.missing


def test_gate_has_version_identifier():
    assert cg.EXTENSION_VERSION and cg.EXTENSION_EDR == "EDR-0006-R2"


def test_gate_is_deterministic():
    rec = {"evidence_class": "OBSERVED"}
    a, b = cg.govern_decision(rec), cg.govern_decision(rec)
    assert a == b, "same record must classify identically (deterministic gate)"


# ── proof transport through the FROZEN event bus ───────────────────────────────────
def test_publish_governed_event_uses_payload_encoding(tmp_path):
    ledger = tmp_path / "ev.jsonl"
    pr = {"evidence_class": "OBSERVED", "audit": {"record_hash": "sha256:abc"}}
    cg.publish_governed_event(type="T", producer="p", mission_id="m",
                              proof_record=pr, path=ledger)
    ev = json.loads(ledger.read_text().strip())
    assert ev.get("payload", {}).get("proof_record") == pr
    assert "sha256:abc" in ev.get("evidence", []), "record_hash must join the evidence chain"
    assert "proof_record" not in ev or ev.get("proof_record") is None, \
        "frozen Event schema must not carry a first-class proof_record field"


# ── dual-encoding extraction: old / new / identical / CONFLICTING / malformed ──────
def test_event_proof_record_old_encoding_only():
    assert cg.event_proof_record({"proof_record": {"x": 1}}) == {"x": 1}


def test_event_proof_record_new_encoding_only():
    assert cg.event_proof_record({"payload": {"proof_record": {"x": 2}}}) == {"x": 2}


def test_event_proof_record_both_identical():
    ev = {"proof_record": {"x": 3}, "payload": {"proof_record": {"x": 3}}}
    assert cg.event_proof_record(ev) == {"x": 3}
    assert cg.proof_encoding_conflict(ev) is False


def test_event_proof_record_conflicting_encodings_fail_closed():
    ev = {"proof_record": {"x": 1}, "payload": {"proof_record": {"x": 2}}}
    assert cg.proof_encoding_conflict(ev) is True
    assert cg.event_proof_record(ev) is None, "conflicting proofs must never merge optimistically"


def test_event_proof_record_malformed_payload():
    assert cg.event_proof_record({"proof_record": ["not", "a", "dict"]}) is None
    assert cg.event_proof_record("not-an-event") is None  # type: ignore[arg-type]


def test_conmon_conflicting_encodings_not_counted_as_carrying(tmp_path, monkeypatch):
    from backend.security import helm_conmon as hc
    ledger = tmp_path / "helm_events.jsonl"
    monkeypatch.setattr(hc, "EVENTS_LEDGER", ledger)
    monkeypatch.setattr(hc, "_adoption_cutoff", lambda: "2026-07-18T00:00:00Z")
    conflicted = {"producer": "council_router", "type": "COUNCIL_SOLVED",
                  "timestamp": "2026-07-19T12:00:00Z",
                  "proof_record": {"evidence_class": "OBSERVED", "governance_state": "GOVERNED"},
                  "payload": {"proof_record": {"evidence_class": "ASSERTED"}}}
    ledger.write_text(json.dumps(conflicted) + "\n")
    cov = hc.governance_coverage()
    assert cov.get("carrying_proof_record", 0) == 0, \
        "an event with conflicting proof encodings must count as NOT carrying (integrity finding)"


# ── model-routing registry failure modes ───────────────────────────────────────────
def _routing(monkeypatch, tmp_path, registry_content):
    reg = tmp_path / "role_bindings.json"
    if registry_content is not None:
        reg.write_text(registry_content)
    monkeypatch.setattr(mr, "REGISTRY_PATH", reg)
    return reg


def test_routing_registry_absent_falls_back_to_frozen(monkeypatch, tmp_path):
    _routing(monkeypatch, tmp_path, None)
    b = mr.resolve_binding("builder")
    assert b["source"] == "frozen_constitutional_fallback"


def test_routing_registry_malformed_fails_closed_to_frozen(monkeypatch, tmp_path):
    _routing(monkeypatch, tmp_path, "{not json !!!")
    b = mr.resolve_binding("builder")
    assert b["source"] == "frozen_constitutional_fallback"


def test_routing_under_attributed_binding_rejected(monkeypatch, tmp_path):
    # ACTIVE but missing authorized_by -> unauthorized mutable config is IGNORED
    _routing(monkeypatch, tmp_path, json.dumps({"bindings": [{
        "role": "builder", "provider": "anthropic", "model": "sneaky-model",
        "effective_at": "2026-07-19T00:00:00Z", "change_record": "none", "status": "ACTIVE"}]}))
    b = mr.resolve_binding("builder")
    assert b["model"] != "sneaky-model" and b["source"] == "frozen_constitutional_fallback"


def test_routing_inactive_binding_ignored(monkeypatch, tmp_path):
    _routing(monkeypatch, tmp_path, json.dumps({"bindings": [{
        "role": "builder", "provider": "anthropic", "model": "future-model",
        "effective_at": "2026-07-19T00:00:00Z", "authorized_by": "founder",
        "change_record": "EDR-X", "status": "PROPOSED"}]}))
    assert mr.resolve_binding("builder")["source"] == "frozen_constitutional_fallback"


def test_routing_unknown_role_is_unresolved_fail_closed(monkeypatch, tmp_path):
    _routing(monkeypatch, tmp_path, None)
    b = mr.resolve_binding("no-such-role")
    assert b["model"] == "UNKNOWN" and b["source"] == "UNRESOLVED"


def test_binding_status_flags_disagreement(monkeypatch, tmp_path):
    _routing(monkeypatch, tmp_path, json.dumps({"bindings": [{
        "role": "builder", "provider": "anthropic", "model": "claude-sonnet-5",
        "effective_at": "2026-07-18T19:00:00Z", "authorized_by": "founder",
        "change_record": "EDR-0006", "status": "ACTIVE"}]}))
    st = mr.binding_status("builder")
    assert st["effective_model"] == "claude-sonnet-5"
    assert st["effective_source"] == "mutable_registry"
    assert st["binding_source"].startswith("coordination/model_routing")
    assert st["registry_authorized"] is True and st["fallback_used"] is False
    # frozen constitutional binding is 'claude' -> registry disagrees -> WARN required
    if st["frozen_fallback_model"] and st["frozen_fallback_model"] != "claude-sonnet-5":
        assert st["bindings_disagree"] is True and st["warning"]


def test_binding_status_rejected_registry_emits_required_telemetry(monkeypatch, tmp_path):
    """Council directive: a malformed/unauthorized registry must surface as
    MUTABLE_REGISTRY_REJECTED with fallback_used=True, registry_authorized=False,
    bindings_disagree=None — never silently reconciled to 'absent'."""
    _routing(monkeypatch, tmp_path, json.dumps({"bindings": [{
        "role": "builder", "provider": "anthropic", "model": "sneaky-model",
        "effective_at": "2026-07-19T00:00:00Z", "change_record": "none", "status": "ACTIVE"}]}))
    st = mr.binding_status("builder")
    assert st["effective_source"] == "frozen_constitutional_fallback"
    assert st["registry_authorized"] is False
    assert st["fallback_used"] is True
    assert st["bindings_disagree"] is None
    assert st["warning"] == "MUTABLE_REGISTRY_REJECTED"
    assert st["registry_entry_state"] == "REJECTED"
    # invariant: the rejected mutable value must NOT appear in ordinary telemetry —
    # an unauthorized/malformed value is diagnostic-only, never a comparison operand
    assert st["registry_model"] is None and "sneaky-model" not in json.dumps(st)
    # malformed registry JSON is also a REJECTION, not absence
    _routing(monkeypatch, tmp_path, "{not json !!!")
    st2 = mr.binding_status("builder")
    assert st2["warning"] == "MUTABLE_REGISTRY_REJECTED" and st2["fallback_used"] is True


# ── structural containment: AUTHORIZED direct readers of the frozen binding file ───
# Finding ROUTING-REGISTRY-DUAL-READ (closure semantics per council 2026-07-19): only the
# specifically identified frozen constitutional fallback reader may directly READ the
# frozen binding file; everything else goes through extensions.model_routing.
AUTHORIZED_DIRECT_READERS = {
    "backend/helm_runtime/provider_router.py": {
        "reason": "FROZEN_CONSTITUTIONAL_FALLBACK — one of the 17 frozen files (d8d5139a); "
                  "cannot be migrated without an in-place frozen edit (prohibited) or a "
                  "ratified EDR re-freeze",
        "manifest": "d8d5139a",
    },
    "backend/helm_runtime/extensions/model_routing.py": {
        "reason": "THE sanctioned resolver — reads the frozen file only as fallback",
        "manifest": None,
    },
    "tests/helm_runtime/test_extensions.py": {
        "reason": "this containment test", "manifest": None,
    },
    # Mentions-only (no file read) — documentation strings, path-classifier fixtures:
    "backend/helm_runtime/mission_contract.py": {
        "reason": "DOCUMENTATION_REFERENCE_ONLY (docstring)", "manifest": None,
    },
    "tests/helm_runtime/test_normalization.py": {
        "reason": "path-string fixture for the normalization classifier; no read",
        "manifest": None,
    },
}


def test_only_authorized_direct_frozen_binding_readers():
    out = subprocess.run(
        ["git", "grep", "--untracked", "-l", "governance/role_bindings", "--", "*.py"],
        cwd=str(ROOT), capture_output=True, text=True,
    ).stdout.strip().splitlines()
    offenders = [p for p in out if p not in AUTHORIZED_DIRECT_READERS]
    assert offenders == [], (
        f"UNAUTHORIZED direct reader(s) of the frozen role_bindings.json: {offenders}. "
        "Use backend.helm_runtime.extensions.model_routing.resolve_binding() "
        "(finding ROUTING-REGISTRY-DUAL-READ).")


def test_authorized_reader_exception_fields_are_exact():
    """The constitutional exception fails closed if any field is absent or changed:
    exact path (no wildcards), reason FROZEN_CONSTITUTIONAL_FALLBACK, manifest d8d5139a
    matching the live manifest id."""
    entry = AUTHORIZED_DIRECT_READERS.get("backend/helm_runtime/provider_router.py")
    assert entry is not None, "the frozen constitutional reader entry is missing — exception void"
    assert entry["reason"].startswith("FROZEN_CONSTITUTIONAL_FALLBACK"), \
        "reason must be FROZEN_CONSTITUTIONAL_FALLBACK — exception void"
    assert entry["manifest"] == "d8d5139a", "manifest identifier changed — exception void"
    for path in AUTHORIZED_DIRECT_READERS:
        assert "*" not in path and path.count("/") >= 1 and path.endswith(".py"), \
            f"wildcard/directory/filename-only exception prohibited: {path}"
    manifest_path = ROOT / "docs" / "evidence" / "audit" / "bridge_verification" / "verification_manifest.json"
    if manifest_path.exists():
        m = json.loads(manifest_path.read_text())
        assert m["verification_target_id"].startswith(entry["manifest"]), \
            "live manifest id no longer matches the exception's manifest — exception void"


def test_frozen_constitutional_reader_and_binding_file_unchanged():
    """The authorized frozen reader is valid ONLY while its bytes (and the frozen binding
    file's bytes) still match the verified manifest — if either drifts, the authorization
    is void and this fails (council directive: fail when the frozen file hash changes)."""
    import hashlib
    manifest_path = ROOT / "docs" / "evidence" / "audit" / "bridge_verification" / "verification_manifest.json"
    if not manifest_path.exists():
        import pytest
        pytest.skip("verification manifest not present in this checkout")
    m = json.loads(manifest_path.read_text())
    for rel in ("backend/helm_runtime/provider_router.py",
                "coordination/governance/role_bindings.json"):
        expected = m["expected_hashes"].get(rel)
        assert expected, f"{rel} missing from frozen manifest"
        actual = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        assert actual == expected, (
            f"FROZEN DRIFT: {rel} no longer matches manifest {m['verification_target_id'][:8]} — "
            "the frozen-reader authorization is void; re-run the A7 process.")
