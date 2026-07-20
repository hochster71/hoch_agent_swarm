"""Tests for the continuous ConMon evidence loop + Rev.5 evidence bundle.

Covers the NEW continuous-monitoring surface (AC8 — "ConMon + NIST 800-53 Rev5 posture
continuous"):
  * backend/security/conmon_evidence.py  — the docs/evidence/conmon bundle emitter
  * scripts/conmon_continuous.py          — the in-process continuous runner + heartbeat

These test the REAL evidence-derived engine (helm_conmon / helm_control_catalog), not the
legacy simulated conmon_manager (that is covered by tests/test_conmon.py). No fake green:
statuses are serialized exactly as assessed; UNKNOWN must contribute zero to posture.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.security import conmon_evidence
from backend.security.helm_control_catalog import CONTROLS


# --------------------------------------------------------------------------- helpers
def _synthetic_posture() -> dict:
    """A deterministic posture that exercises all three statuses (no live assess needed)."""
    controls = [
        {"control_id": "AC-3", "family": "ACCESS CONTROL", "title": "Access Enforcement",
         "status": "IMPLEMENTED", "evidence": "scoped states", "detail": "", "severity": "HIGH"},
        {"control_id": "SC-7", "family": "SYS & COMMS", "title": "Boundary Protection",
         "status": "NOT_IMPLEMENTED", "evidence": "ungated egress", "detail": "", "severity": "HIGH"},
        {"control_id": "SR-3", "family": "SUPPLY CHAIN", "title": "Supply Chain Controls",
         "status": "UNKNOWN", "evidence": "assessor error", "detail": "", "severity": "MODERATE"},
    ]
    return {
        "schema": "HELM_CONTROL_POSTURE_v1",
        "framework": "NIST SP 800-53 Rev. 5",
        "conmon_standard": "NIST SP 800-137",
        "assessed_at": "2026-07-17T16:31:39Z",
        "target_system": "HELM / Hoch Agent Swarm",
        "controls_assessed": 3,
        "implemented": 1,
        "not_implemented": 1,
        "unknown": 1,
        "posture_percent": 33.3,
        "posture_percent_scope": "SAMPLED_CONTROLS_ONLY",
        "open_findings": 2,
        "high_findings": 1,
        "controls": controls,
        "poam": [
            {"poam_id": "POAM-SC-7", "control_id": "SC-7", "title": "Boundary Protection",
             "weakness": "ungated egress", "severity": "HIGH"},
            {"poam_id": "POAM-SR-3", "control_id": "SR-3", "title": "Supply Chain Controls",
             "weakness": "assessor error", "severity": "MODERATE"},
        ],
        "doctrine": "posture is RE-DERIVED from live evidence every cycle",
    }


# --------------------------------------------------------------------------- assess()
def test_assess_math_and_schema(tmp_path):
    """The live engine returns the expected schema and posture is computed correctly."""
    from backend.security.helm_conmon import assess
    p = assess()
    assert p["schema"] == "HELM_CONTROL_POSTURE_v1"
    assert p["framework"] == "NIST SP 800-53 Rev. 5"
    assert p["conmon_standard"] == "NIST SP 800-137"
    # every catalog control is assessed
    assert p["controls_assessed"] == len(CONTROLS)
    assert len(p["controls"]) == len(CONTROLS)
    # posture = implemented / total, UNKNOWN contributes ZERO (never counted implemented)
    expected = round(100.0 * p["implemented"] / p["controls_assessed"], 1)
    assert p["posture_percent"] == expected
    assert p["implemented"] + p["not_implemented"] + p["unknown"] == p["controls_assessed"]
    # scope honesty: never claims full-catalog coverage
    assert p["full_nist_800_53_coverage"] is False
    assert p["posture_percent_scope"] == "SAMPLED_CONTROLS_ONLY"


def test_unknown_never_counts_as_implemented():
    """A control whose assessor could not run must not inflate posture (no fake green)."""
    post = _synthetic_posture()
    impl = [c for c in post["controls"] if c["status"] == "IMPLEMENTED"]
    unk = [c for c in post["controls"] if c["status"] == "UNKNOWN"]
    assert unk, "fixture must include an UNKNOWN control"
    # UNKNOWN is not in the implemented set that drives posture_percent
    assert all(c["status"] != "UNKNOWN" for c in impl)


# ------------------------------------------------------------------- evidence bundle
def test_emit_evidence_writes_full_bundle(tmp_path):
    post = _synthetic_posture()
    manifest = conmon_evidence.emit_evidence(post, evidence_dir=tmp_path)

    # manifest points at real, existing files
    for key in ("posture_json", "posture_md", "control_map_md"):
        rel = manifest["bundle"][key]
        p = conmon_evidence.ROOT / rel
        if not p.exists():
            p = tmp_path / Path(rel).name
        assert p.exists(), f"{key} not written"

    # timestamped json round-trips to the same posture
    json_files = list(tmp_path.glob("conmon_posture_*.json"))
    assert len(json_files) == 1
    reloaded = json.loads(json_files[0].read_text())
    assert reloaded["posture_percent"] == post["posture_percent"]

    # latest.json is a fresh pointer with the current posture summary
    latest = json.loads((tmp_path / "latest.json").read_text())
    assert latest["schema"] == "HELM_CONMON_EVIDENCE_BUNDLE_v1"
    assert latest["framework"] == "NIST SP 800-53 Rev. 5"
    assert latest["posture_percent"] == post["posture_percent"]


def test_control_map_reflects_live_catalog(tmp_path):
    """The Rev.5 control map is regenerated from the live catalog every cycle — so every
    control the engine actually runs appears in the evidence-tree mapping (never stale)."""
    post = _synthetic_posture()
    conmon_evidence.emit_evidence(post, evidence_dir=tmp_path)
    mapping = (tmp_path / "NIST_800-53_REV5_CONTROL_MAP.md").read_text()
    assert "NIST SP 800-53 Rev. 5" in mapping
    for c in CONTROLS:
        assert c["id"] in mapping, f"{c['id']} missing from Rev.5 control map"
        assert c["title"] in mapping


def test_posture_md_reports_findings(tmp_path):
    post = _synthetic_posture()
    conmon_evidence.emit_evidence(post, evidence_dir=tmp_path)
    md = list(tmp_path.glob("conmon_posture_*.md"))[0].read_text()
    assert "POA&M" in md
    assert "POAM-SC-7" in md  # the HIGH finding is surfaced
    assert "No fake green" in md


def test_emit_evidence_loads_posture_from_disk(monkeypatch, tmp_path):
    """With no posture arg, emit_evidence reads the last posture written by assess()."""
    post = _synthetic_posture()
    posture_file = tmp_path / "helm_control_posture.json"
    posture_file.write_text(json.dumps(post))
    monkeypatch.setattr("backend.security.helm_conmon.POSTURE", posture_file)
    out = tmp_path / "out"
    manifest = conmon_evidence.emit_evidence(evidence_dir=out)
    assert manifest["posture_percent"] == post["posture_percent"]


# --------------------------------------------------------------- continuous runner
def test_continuous_single_cycle_writes_heartbeat(monkeypatch, tmp_path):
    """loop(max_cycles=1) runs exactly one real cycle and records a STOPPED heartbeat."""
    import scripts.conmon_continuous as cc
    hb = tmp_path / "conmon_heartbeat.json"
    monkeypatch.setattr(cc, "HEARTBEAT", hb)
    rc = cc.loop(interval=1, max_cycles=1, emit=False)  # emit=False: don't touch docs/evidence
    assert rc == 0
    beat = json.loads(hb.read_text())
    assert beat["schema"] == "HELM_CONMON_HEARTBEAT_v1"
    assert beat["state"] == "STOPPED"
    assert beat["cycles_completed"] == 1
    assert beat["interval_seconds"] == 1
    assert isinstance(beat["pid"], int)


def test_run_cycle_returns_posture(monkeypatch):
    """A single cycle returns a live status snapshot with the Rev.5 posture fields."""
    import scripts.conmon_continuous as cc
    snap = cc.run_cycle(emit=False)
    assert "posture_percent" in snap
    assert snap["controls_assessed"] == len(CONTROLS)
    assert snap["framework"] == "NIST SP 800-53 Rev. 5"


def test_once_flag_runs_single_cycle(monkeypatch, tmp_path):
    """--once is sugar for max-cycles=1; must exit 0 after one cycle without evidence writes."""
    import scripts.conmon_continuous as cc
    monkeypatch.setattr(cc, "HEARTBEAT", tmp_path / "hb.json")
    rc = cc.main(["--once", "--no-evidence"])
    assert rc == 0
    beat = json.loads((tmp_path / "hb.json").read_text())
    assert beat["cycles_completed"] == 1


# ------------------------------------------------------- continuity verifier (N8_CONMON)
def _write_chained_ledger(path: Path, stamps: list[str]) -> None:
    """Build a valid hash-chained ConMon ledger exactly like helm_conmon.assess() does."""
    import hashlib
    prev = "GENESIS"
    with open(path, "a") as f:
        for ts in stamps:
            entry = {"ts": ts, "posture_percent": 84.6, "implemented": 11,
                     "open_findings": 2, "high_findings": 0, "gaps": ["SC-7"],
                     "prev_hash": prev}
            entry["entry_hash"] = hashlib.sha256(
                json.dumps(entry, sort_keys=True).encode()).hexdigest()
            f.write(json.dumps(entry, sort_keys=True) + "\n")
            prev = entry["entry_hash"]


def _write_bundle(evidence_dir: Path) -> None:
    """Emit a real evidence bundle (json+md+control map+latest.json) into evidence_dir."""
    conmon_evidence.emit_evidence(_synthetic_posture(), evidence_dir=evidence_dir)


def test_verifier_passes_on_genuine_continuous_run(tmp_path):
    """All checks PASS when N distinct hash-chained cycles + heartbeat + bundle are present."""
    from scripts import conmon_verify_continuity as v
    ledger = tmp_path / "conmon_ledger.jsonl"
    hb = tmp_path / "conmon_heartbeat.json"
    ev = tmp_path / "conmon"
    stamps = ["2026-07-17T16:00:00Z", "2026-07-17T16:00:02Z", "2026-07-17T16:00:04Z"]
    _write_chained_ledger(ledger, stamps)
    hb.write_text(json.dumps({
        "schema": "HELM_CONMON_HEARTBEAT_v1", "state": "STOPPED", "pid": 4242,
        "cycles_completed": 3, "interval_seconds": 2,
    }))
    _write_bundle(ev)

    checks = v.evaluate_artifacts(cycles=3, ledger_count_before=0,
                                  heartbeat_path=hb, ledger_path=ledger, evidence_dir=ev)
    failed = [c for c in checks if not c["passed"]]
    assert not failed, f"unexpected failures: {failed}"
    names = {c["check"] for c in checks}
    assert "rev5_control_map_covers_live_catalog" in names
    assert "ledger_hashchain_valid" in names


def test_verifier_flags_one_shot_run(tmp_path):
    """A SINGLE snapshot (one-shot) must fail continuity — the whole point of N8."""
    from scripts import conmon_verify_continuity as v
    ledger = tmp_path / "conmon_ledger.jsonl"
    hb = tmp_path / "conmon_heartbeat.json"
    ev = tmp_path / "conmon"
    _write_chained_ledger(ledger, ["2026-07-17T16:00:00Z"])  # only ONE cycle
    hb.write_text(json.dumps({
        "schema": "HELM_CONMON_HEARTBEAT_v1", "state": "STOPPED", "pid": 1,
        "cycles_completed": 1, "interval_seconds": 2}))
    _write_bundle(ev)

    checks = v.evaluate_artifacts(cycles=3, ledger_count_before=0,
                                  heartbeat_path=hb, ledger_path=ledger, evidence_dir=ev)
    by = {c["check"]: c["passed"] for c in checks}
    assert by["ledger_grew_by_cycles"] is False
    assert by["cycles_have_distinct_timestamps"] is False


def test_verifier_detects_tampered_ledger(tmp_path):
    """If the hash chain is broken, ledger_hashchain_valid must FAIL (no fake green)."""
    from scripts import conmon_verify_continuity as v
    ledger = tmp_path / "conmon_ledger.jsonl"
    _write_chained_ledger(ledger, ["2026-07-17T16:00:00Z", "2026-07-17T16:00:02Z"])
    lines = ledger.read_text().splitlines()
    tampered = json.loads(lines[0])
    tampered["posture_percent"] = 100.0  # mutate a field without fixing the hash
    lines[0] = json.dumps(tampered, sort_keys=True)
    ledger.write_text("\n".join(lines) + "\n")

    ok, why = v._ledger_chain_valid(v._read_jsonl(ledger))
    assert ok is False
    assert "hash mismatch" in why or "chain" in why
