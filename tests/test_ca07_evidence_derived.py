"""CA-7 Continuous Monitoring must be EVIDENCE-DERIVED, not self-attested.

`a_ca07_conmon()` used to return IMPLEMENTED unconditionally — a self-attestation, the exact
fake-green the control catalog forbids. These tests pin the corrected behavior: the control is
IMPLEMENTED only when a FRESH Rev.5 evidence bundle and a MULTI-CYCLE hash-chained ConMon ledger
are actually on disk; absence, staleness, or a single one-shot is a FINDING (NOT_IMPLEMENTED).

Everything is exercised against a synthetic repo root (monkeypatched) so the assertion is about
the assessor's logic, not the live posture of this working tree.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend.security import helm_control_catalog as cat


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _seed_root(root: Path, *, generated_at: str, cycles: int, bundle_files: bool = True) -> None:
    """Lay down the artifacts CA-7 reads: an evidence bundle pointer (+ its files) and a ledger."""
    ev = root / "docs" / "evidence" / "conmon"
    ev.mkdir(parents=True, exist_ok=True)
    bundle = {
        "posture_json": "docs/evidence/conmon/conmon_posture_X.json",
        "posture_md": "docs/evidence/conmon/conmon_posture_X.md",
        "control_map_md": "docs/evidence/conmon/NIST_800-53_REV5_CONTROL_MAP.md",
    }
    if bundle_files:
        for rel in bundle.values():
            (root / rel).write_text("evidence\n")
    (ev / "latest.json").write_text(json.dumps({
        "schema": "HELM_CONMON_EVIDENCE_BUNDLE_v1",
        "generated_at": generated_at,
        "framework": "NIST SP 800-53 Rev. 5",
        "posture_percent": 84.6,
        "bundle": bundle,
    }))
    sec = root / "coordination" / "security"
    sec.mkdir(parents=True, exist_ok=True)
    ledger = sec / "conmon_ledger.jsonl"
    with open(ledger, "a") as f:
        for i in range(cycles):
            f.write(json.dumps({"ts": f"2026-07-17T16:0{i}:00Z", "entry_hash": f"h{i}"}) + "\n")


def test_ca07_implemented_on_fresh_multicycle_evidence(monkeypatch, tmp_path):
    monkeypatch.setattr(cat, "ROOT", tmp_path)
    _seed_root(tmp_path, generated_at=_iso(datetime.now(timezone.utc)), cycles=3)
    r = cat.a_ca07_conmon()
    assert r["status"] == cat.IMPLEMENTED, r
    assert "hash-chained cycles" in r["evidence"]


def test_ca07_not_implemented_without_any_bundle(monkeypatch, tmp_path):
    """No evidence bundle at all — absence of evidence is a finding, not green."""
    monkeypatch.setattr(cat, "ROOT", tmp_path)
    r = cat.a_ca07_conmon()
    assert r["status"] == cat.NOT_IMPLEMENTED
    assert "no ConMon evidence bundle" in r["evidence"]


def test_ca07_stale_evidence_is_a_finding(monkeypatch, tmp_path):
    """A bundle older than the freshness window means monitoring stopped — NOT_IMPLEMENTED."""
    monkeypatch.setattr(cat, "ROOT", tmp_path)
    old = datetime.now(timezone.utc) - timedelta(seconds=cat.CA7_MAX_EVIDENCE_AGE_SEC + 3600)
    _seed_root(tmp_path, generated_at=_iso(old), cycles=3)
    r = cat.a_ca07_conmon()
    assert r["status"] == cat.NOT_IMPLEMENTED
    assert "STALE" in r["evidence"]


def test_ca07_single_one_shot_does_not_qualify(monkeypatch, tmp_path):
    """A fresh bundle but only ONE ledger cycle is a one-shot, not continuous monitoring."""
    monkeypatch.setattr(cat, "ROOT", tmp_path)
    _seed_root(tmp_path, generated_at=_iso(datetime.now(timezone.utc)), cycles=1)
    r = cat.a_ca07_conmon()
    assert r["status"] == cat.NOT_IMPLEMENTED
    assert "one-shot" in r["detail"] or "cycle" in r["evidence"]


def test_ca07_missing_referenced_files_is_a_finding(monkeypatch, tmp_path):
    """latest.json can name files that do not exist — that is a broken bundle, never green."""
    monkeypatch.setattr(cat, "ROOT", tmp_path)
    _seed_root(tmp_path, generated_at=_iso(datetime.now(timezone.utc)), cycles=3,
               bundle_files=False)
    r = cat.a_ca07_conmon()
    assert r["status"] == cat.NOT_IMPLEMENTED
    assert "missing files" in r["evidence"]


def test_ca07_is_no_longer_hardcoded_green(monkeypatch, tmp_path):
    """Regression guard: on an empty root the control must NOT self-attest IMPLEMENTED."""
    monkeypatch.setattr(cat, "ROOT", tmp_path)
    assert cat.a_ca07_conmon()["status"] != cat.IMPLEMENTED
