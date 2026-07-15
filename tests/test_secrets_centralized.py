"""Provider credentials must flow through the single config layer (backend/config/secrets.py).

Two guarantees:
  1. RATCHET: no NEW code in backend/ reads a provider API key directly from the
     environment. A small allowlist documents the known legacy readers still to be
     migrated; anything else fails this test, so the sprawl cannot grow.
  2. The SECRETS API resolves aliases, fails closed on missing keys, and never leaks
     secret VALUES through audit surfaces (configured_providers -> booleans only).
"""
import os
import re
from pathlib import Path

import pytest

from backend.config.secrets import SECRETS, PROVIDER_KEY_ENV_NAMES

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"

# Known legacy direct-readers still to be migrated onto SECRETS. This list may only
# SHRINK. agent_executor.py is intentionally NOT here — it was migrated; if it
# regresses, this test must fail.
LEGACY_ALLOWLIST = {
    "backend/main.py",                          # bool(os.getenv("GOOGLE_API_KEY")) health flag
    "backend/model_router/google_frontier.py",  # direct google key read
    "backend/voice/elevenlabs_tts.py",          # ELEVENLABS_* read
}

_READ = re.compile(
    r"""os\.(?:environ\.get|getenv)\(\s*["'](%s)["']"""
    % "|".join(sorted(re.escape(n) for n in PROVIDER_KEY_ENV_NAMES))
)


def _offenders():
    bad = {}
    for py in BACKEND.rglob("*.py"):
        rel = py.relative_to(ROOT).as_posix()
        if "__pycache__" in rel or rel == "backend/config/secrets.py":
            continue
        hits = _READ.findall(py.read_text(encoding="utf-8", errors="ignore"))
        if hits:
            bad[rel] = sorted(set(hits))
    return bad


def test_no_new_direct_provider_key_reads_in_backend():
    offenders = _offenders()
    unexpected = {f: k for f, k in offenders.items() if f not in LEGACY_ALLOWLIST}
    assert not unexpected, (
        "New direct provider-key reads (route them through backend.config.secrets.SECRETS): "
        + "; ".join(f"{f}:{k}" for f, k in unexpected.items())
    )


def test_allowlist_only_shrinks():
    # every allowlisted file must still exist and still actually read a key — dead
    # allowlist entries should be removed so the ratchet stays honest.
    offenders = _offenders()
    stale = [f for f in LEGACY_ALLOWLIST if f not in offenders]
    assert not stale, f"allowlist entries no longer read a key (remove them): {stale}"


def test_agent_executor_is_migrated():
    txt = (BACKEND / "agent_executor.py").read_text(encoding="utf-8")
    assert "SECRETS.provider_key(" in txt
    assert not _READ.search(txt), "agent_executor.py regressed to a direct key read"


def test_alias_resolution(monkeypatch):
    for n in PROVIDER_KEY_ENV_NAMES:
        monkeypatch.delenv(n, raising=False)
    monkeypatch.setenv("XAI_API_KEY", "xk")
    monkeypatch.setenv("GEMINI_API_KEY", "gk")
    assert SECRETS.provider_key("xai") == "xk"
    assert SECRETS.provider_key("grok") == "xk"          # alias -> xai
    assert SECRETS.provider_key("gemini") == "gk"
    assert SECRETS.provider_key("google") == "gk"        # alias -> gemini
    assert SECRETS.has("xai") and not SECRETS.has("openai")


def test_require_fails_closed(monkeypatch):
    for n in PROVIDER_KEY_ENV_NAMES:
        monkeypatch.delenv(n, raising=False)
    with pytest.raises(RuntimeError):
        SECRETS.require("anthropic")


def test_configured_providers_leaks_no_values(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "super-secret-value")
    conf = SECRETS.configured_providers()
    assert conf["openai"] is True
    assert all(isinstance(v, bool) for v in conf.values())
    assert "super-secret-value" not in repr(conf)
