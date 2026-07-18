"""Regression: test/tmp scheduler context must never leak into the canonical production
runtime pointer (coordination/council/active_runtime_source.json).

On 2026-07-18 a test built a PersistentScheduler with a pytest tmp evidence_dir and
publish_runtime_source=True; runtime_source.publish() wrote that pytest path as the
canonical pointer, so the independent observer saw the canonical lease ledger pointing at a
directory that no longer exists and flagged the runtime CONTRADICTED. These tests prove the
guard and that the live production pointer never references a pytest temp path.
"""
import json
import tempfile
from pathlib import Path

import backend.truth.runtime_source as rs


def test_ephemeral_evidence_is_detected():
    tmp = Path(tempfile.mkdtemp())
    assert rs._is_ephemeral_evidence(tmp) is True
    assert rs._is_ephemeral_evidence(Path("/private/var/folders/x/pytest-of-me/pytest-1/evid")) is True
    # A normal in-repo production evidence dir is NOT ephemeral (ignoring the pytest env
    # guard, which is asserted separately below).


def test_publish_never_writes_canonical_pointer_for_tmp_evidence(monkeypatch):
    """publish() with a tmp evidence_dir must NOT write the canonical POINTER — it may only
    write the local sidecar inside the throwaway dir."""
    fake_pointer = Path(tempfile.mkdtemp()) / "active_runtime_source.json"
    monkeypatch.setattr(rs, "POINTER", fake_pointer)
    tmp_evidence = Path(tempfile.mkdtemp())

    rs.publish(tmp_evidence, "test-instance-xyz")

    assert not fake_pointer.exists(), "canonical pointer must not be written for tmp/test evidence"
    # the local sidecar IS written (test scheduler still has its own context)
    assert (tmp_evidence / rs.INSTANCE_SIDECAR_NAME).exists()


def test_pytest_env_marks_even_a_production_looking_path_ephemeral():
    """Belt-and-suspenders: PYTEST_CURRENT_TEST is set during any test run, so even a
    production-looking evidence path is treated as ephemeral — publish() will never write
    the canonical pointer while a test is executing. Pure predicate check (no FS write)."""
    import os
    assert os.environ.get("PYTEST_CURRENT_TEST") is not None  # we are under pytest now
    assert rs._is_ephemeral_evidence(Path("/some/production/looking/dir")) is True


def test_live_canonical_pointer_never_references_pytest_temp():
    """The ACTUAL production pointer must never reference a pytest temp directory."""
    if not rs.POINTER.exists():
        return  # nothing published yet is acceptable
    doc = json.loads(rs.POINTER.read_text(encoding="utf-8"))
    for field in ("ledger_path", "evidence_dir", "instance_sidecar"):
        val = str(doc.get(field, ""))
        assert "pytest-" not in val, f"{field} references a pytest temp path: {val}"
        assert "/pytest-of-" not in val, f"{field} references a pytest temp path: {val}"
