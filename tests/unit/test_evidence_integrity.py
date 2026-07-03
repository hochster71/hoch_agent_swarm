"""Tamper-evident evidence manifest tests (C3).

Covers the two attacks the old evidence_tamper_gate.sh missed:
  (a) edit an artifact  -> hash mismatch
  (b) edit the manifest -> MAC mismatch
  (c) replace the whole manifest with a self-consistent forgery -> anchor miss
"""
import subprocess
from pathlib import Path

import pytest

from backend.mission_control import evidence_integrity as ei


@pytest.fixture()
def founder_key(tmp_path):
    key = tmp_path / "fk"
    subprocess.run(["ssh-keygen", "-t", "ed25519", "-N", "", "-q", "-f", str(key)], check=True)
    return key


@pytest.fixture()
def workspace(tmp_path):
    art = tmp_path / "artifacts"
    art.mkdir()
    (art / "a.json").write_text('{"result": "pass"}')
    (art / "b.log").write_text("all gates green")
    return tmp_path


def _build(workspace, founder_key, anchor):
    paths = [workspace / "artifacts" / "a.json", workspace / "artifacts" / "b.log"]
    return ei.build_manifest(paths, "run-1", founder_key=founder_key, anchor_log=anchor)


def test_clean_manifest_verifies(workspace, founder_key, tmp_path):
    anchor = tmp_path / "anchor.log"
    m = _build(workspace, founder_key, anchor)
    r = ei.verify_manifest(m, base_dir=workspace, founder_key=founder_key, anchor_log=anchor)
    assert r["ok"], r


def test_edited_artifact_detected(workspace, founder_key, tmp_path):
    anchor = tmp_path / "anchor.log"
    m = _build(workspace, founder_key, anchor)
    (workspace / "artifacts" / "a.json").write_text('{"result": "FAIL-hidden"}')
    r = ei.verify_manifest(m, base_dir=workspace, founder_key=founder_key, anchor_log=anchor)
    assert not r["ok"] and "hash mismatch" in r["reason"]


def test_edited_manifest_hash_detected(workspace, founder_key, tmp_path):
    """Agent rewrites both artifact and its manifest hash — MAC still fails."""
    anchor = tmp_path / "anchor.log"
    m = _build(workspace, founder_key, anchor)
    (workspace / "artifacts" / "a.json").write_text('{"result": "FAIL-hidden"}')
    m["artifacts"][0]["sha256"] = ei._sha256_file(workspace / "artifacts" / "a.json")
    r = ei.verify_manifest(m, base_dir=workspace, founder_key=founder_key, anchor_log=anchor)
    assert not r["ok"] and "MAC" in r["reason"]


def test_forged_manifest_without_key_fails_anchor(workspace, founder_key, tmp_path):
    """Attacker without the founder key builds a self-consistent manifest using
    a rogue key. MAC is internally consistent but absent from external anchor."""
    anchor = tmp_path / "anchor.log"
    _build(workspace, founder_key, anchor)  # legit anchor entry exists
    rogue = tmp_path / "rogue"
    subprocess.run(["ssh-keygen", "-t", "ed25519", "-N", "", "-q", "-f", str(rogue)], check=True)
    # forged manifest built with rogue key, NOT anchored
    forged = ei.build_manifest(
        [workspace / "artifacts" / "a.json"], "run-forge",
        founder_key=rogue, anchor_log=tmp_path / "rogue_anchor.log")
    r = ei.verify_manifest(forged, base_dir=workspace, founder_key=founder_key, anchor_log=anchor)
    assert not r["ok"] and ("MAC" in r["reason"] or "anchor" in r["reason"])


def test_missing_anchor_fails_closed(workspace, founder_key, tmp_path):
    anchor = tmp_path / "anchor.log"
    m = _build(workspace, founder_key, anchor)
    r = ei.verify_manifest(m, base_dir=workspace, founder_key=founder_key,
                           anchor_log=tmp_path / "nonexistent.log")
    assert not r["ok"]
