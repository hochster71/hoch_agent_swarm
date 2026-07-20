"""N3-VERDICT-BINDING-GAP regression guard (2026-07-20, founder-directed).

A clean 'OVERALL: VERIFIED' verdict must NOT satisfy N3_VERIFY unless it mechanically
proves BINDING (candidate HEAD + tree sha embedded), SCOPE (composed-runtime attested),
and VINTAGE/PROVENANCE (no method disclaimer). Misbound => HOLD, never DONE.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FAKE_HEAD = "a" * 40
FAKE_TREE = "b" * 40


def _load_runner():
    spec = importlib.util.spec_from_file_location(
        "helm_goal_runner_n3_test", ROOT / "scripts" / "helm_goal_runner.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _setup(m, tmp_path, monkeypatch, verdict_text):
    monkeypatch.setattr(m, "_N3_ROOT", tmp_path)
    monkeypatch.setattr(m, "_n3_candidate_ids", lambda: (FAKE_HEAD, FAKE_TREE))
    (tmp_path / "verdict.md").write_text(verdict_text)
    return {"id": "N3_VERIFY", "status": "DONE", "verdict": "VERIFIED", "evidence": "verdict.md"}


GOOD = (f"Verdict bound to candidate commit {FAKE_HEAD} tree {FAKE_TREE}\n"
        "SCOPE: COMPOSED_RUNTIME (restored core + extension boundary + gate + transport + "
        "dual-decode + routing registry + rewired sites + adversarial matrix)\n"
        "Method: independent re-execution and re-hashing performed.\n"
        "OVERALL: VERIFIED\n")


def test_fully_bound_verdict_is_done(tmp_path, monkeypatch):
    m = _load_runner()
    n = _setup(m, tmp_path, monkeypatch, GOOD)
    assert m._effective_status(n) == "DONE"


def test_content_hash_only_verdict_holds(tmp_path, monkeypatch):
    """The exact 2026-07-20 incident: real VERIFIED verdict bound to a content hash,
    no candidate SHA/tree - must HOLD."""
    m = _load_runner()
    n = _setup(m, tmp_path, monkeypatch,
               "Bound verification_target_id d8d5139a" + "0" * 56 + "\n"
               "SCOPE: COMPOSED_RUNTIME\nOVERALL: VERIFIED\n")
    assert m._effective_status(n) == "HOLD"


def test_narrower_scope_holds(tmp_path, monkeypatch):
    m = _load_runner()
    n = _setup(m, tmp_path, monkeypatch,
               GOOD.replace("SCOPE: COMPOSED_RUNTIME", "SCOPE: BRIDGE_ONLY"))
    assert m._effective_status(n) == "HOLD"


def test_disclaimed_method_holds(tmp_path, monkeypatch):
    m = _load_runner()
    n = _setup(m, tmp_path, monkeypatch,
               GOOD + "\nThis is NOT independent re-execution of the implementation.\n")
    assert m._effective_status(n) == "HOLD"


def test_missing_evidence_file_holds(tmp_path, monkeypatch):
    m = _load_runner()
    n = _setup(m, tmp_path, monkeypatch, GOOD)
    n["evidence"] = "no_such_verdict.md"
    assert m._effective_status(n) == "HOLD"


def test_non_verified_overall_holds(tmp_path, monkeypatch):
    m = _load_runner()
    n = _setup(m, tmp_path, monkeypatch, GOOD.replace("OVERALL: VERIFIED", "OVERALL: PENDING"))
    assert m._effective_status(n) == "HOLD"


def test_crashing_check_fails_closed(tmp_path, monkeypatch):
    m = _load_runner()
    n = _setup(m, tmp_path, monkeypatch, GOOD)
    def boom(): raise RuntimeError("git unavailable")
    monkeypatch.setattr(m, "_n3_candidate_ids", boom)
    assert m._effective_status(n) == "HOLD"


def test_non_n3_nodes_unaffected(tmp_path, monkeypatch):
    m = _load_runner()
    _setup(m, tmp_path, monkeypatch, GOOD)
    assert m._effective_status({"id": "N5_KNOWLEDGE", "status": "DONE"}) == "DONE"
    assert m._effective_status({"id": "N3_VERIFY", "status": "PENDING"}) == "PENDING"
