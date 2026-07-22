"""Focused security tests for scripts/founder/asc_credentials_gate.py
(founder-required before the ASC credential ceremony, 2026-07-22).

Proves, against the production gate code, with Apple and the goal validators
fully faked (no network, no repo mutation — every run is re-rooted into an
isolated temp directory):

  S1  pasted PEM contents are NEVER written to disk anywhere under ROOT
  S2  an invalid paste (not a path, not PEM) persists nothing and exits
  S3  Apple rejection (bad key id / issuer id / key) persists nothing
  S4  a valid .p8 PATH persists the path only — key bytes never copied
  S5  .env is created 0600 from birth, updated atomically, unrelated keys
      preserved, and no temp artifacts are left behind (success AND failure)
  S6  stdout/stderr never contain PEM material or a bearer token
  S7  a group/other-readable .p8 triggers the warning (warn-only)
  S8  the live signing path (scripts/goal/asc_client.py) consumes the key
      from memory — no tempfile mechanism exists in it
"""
from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
import sys
import types
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
FAKE_PEM = ("-----BEGIN PRIVATE KEY-----\n"
            "FAKEFAKEFAKEFAKEFAKEFAKEFAKEFAKE\n"
            "-----END PRIVATE KEY-----")


def _load_gate():
    spec = importlib.util.spec_from_file_location(
        "asc_credentials_gate",
        REPO / "scripts" / "founder" / "asc_credentials_gate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _FakeASC(types.ModuleType):
    """Stand-in for goal.asc_client: full control, zero network."""

    class ASCUnavailable(Exception):
        pass

    DEFAULT_BUNDLE_ID = "com.epicfury.dashboard"

    def __init__(self, accept: bool):
        super().__init__("goal.asc_client")
        self._accept = accept
        self.ASCUnavailable = _FakeASC.ASCUnavailable

    def _app_id(self, bundle_id):
        if not self._accept:
            raise self.ASCUnavailable("401 from App Store Connect (bad/expired credentials)")
        return "APP123"

    def _get(self, path, params=None):
        return {"data": [{"attributes": {"appStoreState": "READY_FOR_SALE",
                                         "versionString": "1.0.2"}}]}


def _run_gate(tmp_path, monkeypatch, capsys, prompts, accept=True):
    """Drive main() with scripted prompts inside an isolated ROOT."""
    mod = _load_gate()
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(mod, "_ensure_deps", lambda: None)
    answers = list(prompts)
    monkeypatch.setattr(mod, "_prompt_hidden",
                        lambda label, env: answers.pop(0))
    # the trailing validator re-runs must never execute real scripts here
    ran = []
    monkeypatch.setattr(mod.subprocess, "run",
                        lambda cmd, **kw: ran.append(cmd) or
                        subprocess.CompletedProcess(cmd, 0, "", ""))
    fake = _FakeASC(accept)
    pkg = types.ModuleType("goal")
    pkg.asc_client = fake
    monkeypatch.setitem(sys.modules, "goal", pkg)
    monkeypatch.setitem(sys.modules, "goal.asc_client", fake)
    for var in ("APP_STORE_CONNECT_KEY_ID", "APP_STORE_CONNECT_ISSUER_ID",
                "ASC_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    code = None
    try:
        code = mod.main()
    except SystemExit as e:
        code = e.code
    out = capsys.readouterr()
    return mod, code, out.out + out.err, ran


def _files_containing(root: Path, needle: str):
    hits = []
    for p in root.rglob("*"):
        if p.is_file():
            try:
                if needle in p.read_text(errors="ignore"):
                    hits.append(p)
            except OSError:
                pass
    return hits


# ---- S1 / S6: pasted PEM stays in memory only -------------------------------------

def test_s1_pasted_pem_never_written_to_disk(tmp_path, monkeypatch, capsys):
    mod, code, output, _ = _run_gate(
        tmp_path, monkeypatch, capsys, ["KEYID123", "ISSUER456", FAKE_PEM])
    assert code == 0
    assert _files_containing(tmp_path, "BEGIN PRIVATE KEY") == []
    env = (tmp_path / ".env").read_text()
    assert "ASC_API_KEY" not in env  # raw PEM mode: not even a placeholder
    assert "APP_STORE_CONNECT_KEY_ID=KEYID123" in env
    assert "Raw PEM was NOT persisted" in output


def test_s6_output_never_contains_secret_material(tmp_path, monkeypatch, capsys):
    for accept in (True, False):
        _, code, output, _ = _run_gate(
            tmp_path / str(accept), monkeypatch, capsys,
            ["KEYID123", "ISSUER456", FAKE_PEM], accept=accept)
        blob = output + str(code)  # exit messages included in the secret scan
        assert "BEGIN PRIVATE KEY" not in blob
        assert "FAKEFAKE" not in blob
        assert "Bearer " not in blob


# ---- S2 / S3: invalid input and Apple rejection persist nothing -------------------

def test_s2_invalid_paste_persists_nothing(tmp_path, monkeypatch, capsys):
    _, code, _, ran = _run_gate(
        tmp_path, monkeypatch, capsys,
        ["KEYID123", "ISSUER456", "/no/such/AuthKey_X.p8"])
    assert code not in (0, None)
    assert not (tmp_path / ".env").exists()
    assert not (tmp_path / "coordination").exists()
    assert ran == []  # no validator re-runs on failure


def test_s3_apple_rejection_persists_nothing(tmp_path, monkeypatch, capsys):
    _, code, output, ran = _run_gate(
        tmp_path, monkeypatch, capsys,
        ["BADKEY", "BADISSUER", FAKE_PEM], accept=False)
    assert code not in (0, None)
    assert not (tmp_path / ".env").exists()
    assert not (tmp_path / "coordination").exists()
    assert ran == []
    # sys.exit(message) carries the reason in the SystemExit code, not stdout
    assert "FAIL-CLOSED" in str(code)


# ---- S4: path mode persists the path only -----------------------------------------

def test_s4_valid_path_persists_path_only(tmp_path, monkeypatch, capsys):
    key = tmp_path / "keys" / "AuthKey_TEST.p8"
    key.parent.mkdir()
    key.write_text(FAKE_PEM)
    key.chmod(0o600)
    mod, code, output, ran = _run_gate(
        tmp_path, monkeypatch, capsys, ["KEYID123", "ISSUER456", str(key)])
    assert code == 0
    env = (tmp_path / ".env").read_text()
    assert f"ASC_API_KEY={key}" in env
    assert "BEGIN PRIVATE KEY" not in env
    # the only PEM on disk is the founder's own key file
    assert _files_containing(tmp_path, "BEGIN PRIVATE KEY") == [key]
    # evidence snapshot written from live (faked) state, no secrets inside
    snap = json.loads((tmp_path / "coordination" / "evidence" / "external" /
                       "asc_epic_fury.json").read_text())
    assert snap["appStoreState"] == "READY_FOR_SALE"
    assert ran, "validator recompute chain should run on success"


# ---- S5: atomic 0600 .env, unrelated keys preserved, no temp litter ---------------

def test_s5_env_created_0600_and_atomic(tmp_path, monkeypatch, capsys):
    (tmp_path / ".env").write_text("UNRELATED=keepme\n")
    os.chmod(tmp_path / ".env", 0o600)
    _, code, _, _ = _run_gate(
        tmp_path, monkeypatch, capsys, ["KEYID123", "ISSUER456", FAKE_PEM])
    assert code == 0
    env_path = tmp_path / ".env"
    assert stat.S_IMODE(env_path.stat().st_mode) == 0o600
    env = env_path.read_text()
    assert "UNRELATED=keepme" in env
    assert list(tmp_path.glob(".env.*.tmp")) == []  # nothing left behind


def test_s5b_fresh_env_is_0600_from_birth_and_failure_leaves_no_temp(
        tmp_path, monkeypatch, capsys):
    mod = _load_gate()
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    # success path: brand-new .env must be 0600
    mod._upsert_env_file(tmp_path / ".env", {"A": "1"})
    assert stat.S_IMODE((tmp_path / ".env").stat().st_mode) == 0o600
    # failure path: os.replace blows up -> temp removed, target intact
    monkeypatch.setattr(mod.os, "replace",
                        lambda a, b: (_ for _ in ()).throw(OSError("boom")))
    with pytest.raises(OSError):
        mod._upsert_env_file(tmp_path / ".env", {"B": "2"})
    assert list(tmp_path.glob(".env.*.tmp")) == []
    assert (tmp_path / ".env").read_text() == "A=1\n"  # prior content preserved


# ---- S7: permissive .p8 warning (warn-only, never chmods) -------------------------

def test_s7_permissive_p8_warns_but_never_chmods(tmp_path, monkeypatch, capsys):
    key = tmp_path / "AuthKey_LOOSE.p8"
    key.write_text(FAKE_PEM)
    key.chmod(0o644)
    _, code, output, _ = _run_gate(
        tmp_path, monkeypatch, capsys, ["KEYID123", "ISSUER456", str(key)])
    assert code == 0
    assert "WARNING" in output and "chmod 600" in output
    assert stat.S_IMODE(key.stat().st_mode) == 0o644  # warn-only: untouched


# ---- S8: signing consumes the key from memory (no tempfile path exists) -----------

def test_s8_asc_client_signs_from_memory_no_tempfile():
    src = (REPO / "scripts" / "goal" / "asc_client.py").read_text()
    assert "tempfile" not in src
    assert "NamedTemporary" not in src
    assert "mkstemp" not in src
    # the key flows as a string straight into jwt.encode
    assert "jwt.encode(payload, _load_private_key()" in src
