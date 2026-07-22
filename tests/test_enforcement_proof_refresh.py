"""Negative / regression tests for the enforcement-proof evidence chain
(founder verification items, 2026-07-22).

Proves, against the production refresh + verify code:
  N1  a failing validator emits NO proof package and leaves the stable
      pointer untouched (requirement then ages out — fail-closed)
  N2  a pass below the required minimum count emits nothing
  N3  a validator error run (rc!=0) emits nothing even if 'passed' appears
  N4  the ONLY execution path is the real pytest entry point on the real
      suite (no alternate path can fabricate a PASS artifact)
  N5  validator drift after a proof is written => verifier INVALID
  N6  config drift after a proof is written    => verifier INVALID
  N7  tampered pointer (edited counts) diverges from the immutable package
      => verifier INVALID
  N8  the live goal_requirements.json maps REQ-GOV-002/003 and REQ-ES-002 to
      proof-pointer evidence, NOT to production source files (mapping check)

All refresher runs execute inside a temp root — the real coordination tree is
never written by this suite (NO FAKE GREEN applies to tests too).
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _load(mod_name: str):
    spec = importlib.util.spec_from_file_location(
        mod_name, REPO / "scripts" / "goal" / f"{mod_name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def rep(tmp_path, monkeypatch):
    """The refresher module, re-rooted into an isolated temp repo."""
    mod = _load("refresh_enforcement_proofs")
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(mod, "PACKAGE_DIR",
                        tmp_path / "coordination" / "council" / "live_proof_packages")
    # materialize every bound file inside the temp root
    for spec_ in mod.REQUIREMENTS.values():
        for rel in [spec_["suite"], *spec_["production_evidence"]]:
            p = tmp_path / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(f"# bound file stand-in: {rel}\n")
        (tmp_path / spec_["stable_pointer"]).parent.mkdir(parents=True, exist_ok=True)
    cfg = tmp_path / mod.CONFIG_PATH
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(json.dumps({"requirements": [
        {"id": rid, "evidence_path": s["stable_pointer"], "freshness_sla_hours": 168}
        for rid, s in mod.REQUIREMENTS.items()]}))
    return mod


def _fake_run(returncode: int, stdout: str):
    def _f(spec):
        return subprocess.CompletedProcess(args=["pytest"], returncode=returncode,
                                           stdout=stdout, stderr="")
    return _f


def _pointer(mod, req_id: str) -> Path:
    return mod.ROOT / mod.REQUIREMENTS[req_id]["stable_pointer"]


# ---- N1 / N2 / N3: failing runs must write nothing --------------------------------

def test_n1_failing_suite_writes_nothing(rep, monkeypatch):
    monkeypatch.setattr(rep, "_run_validator",
                        _fake_run(1, "3 passed, 2 failed in 1.0s"))
    assert rep.refresh("REQ-ES-002") is False
    assert not _pointer(rep, "REQ-ES-002").exists()
    assert not rep.PACKAGE_DIR.exists() or not any(rep.PACKAGE_DIR.iterdir())


def test_n1b_failing_suite_never_clobbers_existing_pointer(rep, monkeypatch):
    ptr = _pointer(rep, "REQ-ES-002")
    ptr.write_text('{"sentinel": "prior-good-proof"}')
    monkeypatch.setattr(rep, "_run_validator",
                        _fake_run(1, "0 passed, 5 failed in 1.0s"))
    assert rep.refresh("REQ-ES-002") is False
    assert json.loads(ptr.read_text()) == {"sentinel": "prior-good-proof"}


def test_n2_pass_below_min_count_writes_nothing(rep, monkeypatch):
    # REQ-GOV-002 requires >= 24 proofs; 5 passing is not acceptance
    monkeypatch.setattr(rep, "_run_validator", _fake_run(0, "5 passed in 1.0s"))
    assert rep.refresh("REQ-GOV-002") is False
    assert not _pointer(rep, "REQ-GOV-002").exists()


def test_n3_error_rc_writes_nothing_despite_passed_text(rep, monkeypatch):
    monkeypatch.setattr(rep, "_run_validator",
                        _fake_run(2, "28 passed, 1 error in 1.0s"))
    assert rep.refresh("REQ-GOV-002") is False
    assert not _pointer(rep, "REQ-GOV-002").exists()


# ---- N4: single authentic execution path -----------------------------------------

def test_n4_validator_invoked_is_real_pytest_on_real_suite(rep, monkeypatch):
    captured = {}

    def spy(cmd, **kw):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(args=cmd, returncode=1,
                                           stdout="1 failed", stderr="")
    monkeypatch.setattr(rep.subprocess, "run", spy)
    rep.refresh("REQ-ES-002")
    cmd = captured["cmd"]
    assert cmd[0] == sys.executable
    assert cmd[1:3] == ["-m", "pytest"]
    assert rep.REQUIREMENTS["REQ-ES-002"]["suite"] in cmd


def test_n4b_no_alternate_pass_writer_exists(rep):
    # Structural guarantee: the stable pointer is written at exactly one call
    # site, inside refresh(); nothing else in the module writes it.
    src = (REPO / "scripts" / "goal" / "refresh_enforcement_proofs.py").read_text()
    assert src.count("pointer.write_text") == 1
    assert "stable_pointer" in src.split("if not ok:")[1], \
        "pointer write must come only after the fail-closed guard"


# ---- N5 / N6 / N7: verifier invalidates drifted or tampered proofs ----------------

@pytest.fixture()
def written_proof(rep, monkeypatch):
    # the isolated temp root is not a git repo; bind to a stand-in commit id
    monkeypatch.setattr(rep, "_git", lambda *a: "deadbeef" * 5)
    monkeypatch.setattr(rep, "_run_validator", _fake_run(0, "28 passed in 2.0s"))
    assert rep.refresh("REQ-GOV-002") is True
    ver = _load("verify_enforcement_proofs")
    monkeypatch.setattr(ver, "ROOT", rep.ROOT)
    monkeypatch.setattr(ver, "_load_specs", lambda: (rep.REQUIREMENTS, rep.SCHEMA))
    cfg = json.loads((rep.ROOT / rep.CONFIG_PATH).read_text())
    return rep, ver, cfg


def test_baseline_fresh_proof_is_valid(written_proof):
    rep_, ver, cfg = written_proof
    assert ver.verify("REQ-GOV-002", rep_.REQUIREMENTS["REQ-GOV-002"],
                      rep_.SCHEMA, cfg) == []


def test_n5_validator_drift_invalidates_old_proof(written_proof):
    rep_, ver, cfg = written_proof
    suite = rep_.ROOT / rep_.REQUIREMENTS["REQ-GOV-002"]["suite"]
    suite.write_text(suite.read_text() + "\n# validator changed\n")
    fails = ver.verify("REQ-GOV-002", rep_.REQUIREMENTS["REQ-GOV-002"],
                       rep_.SCHEMA, cfg)
    assert any("VALIDATOR DRIFT" in f for f in fails)


def test_n6_config_drift_invalidates_old_proof(written_proof):
    rep_, ver, cfg = written_proof
    cfg_path = rep_.ROOT / rep_.CONFIG_PATH
    cfg_path.write_text(cfg_path.read_text() + "\n")
    fails = ver.verify("REQ-GOV-002", rep_.REQUIREMENTS["REQ-GOV-002"],
                       rep_.SCHEMA, json.loads(cfg_path.read_text()))
    assert any("CONFIG DRIFT" in f for f in fails)


def test_n7_tampered_pointer_diverges_from_package(written_proof):
    rep_, ver, cfg = written_proof
    ptr = rep_.ROOT / rep_.REQUIREMENTS["REQ-GOV-002"]["stable_pointer"]
    rec = json.loads(ptr.read_text())
    rec["result"]["passed"] = 9999  # fabricate a better result
    ptr.write_text(json.dumps(rec, indent=2))
    fails = ver.verify("REQ-GOV-002", rep_.REQUIREMENTS["REQ-GOV-002"],
                       rep_.SCHEMA, cfg)
    assert any(f.startswith("B9") for f in fails)


# ---- N8: live repo mapping (read-only against the REAL config) --------------------

def test_n8_live_config_maps_requirements_to_proof_pointers():
    cfg = json.loads((REPO / "config" / "goal_requirements.json").read_text())
    by_id = {r["id"]: r for r in cfg["requirements"]}
    expected = {
        "REQ-GOV-002": "coordination/council/h1b_enforcement_proof.json",
        "REQ-GOV-003": "coordination/council/h1b_quorum_proof.json",
        "REQ-ES-002": "coordination/council/h1d_dispatch_proof.json",
    }
    for rid, pointer in expected.items():
        assert by_id[rid]["evidence_path"] == pointer, rid
        # source stays traceability evidence in the note, never freshness evidence
        assert not by_id[rid]["evidence_path"].endswith(".py")
