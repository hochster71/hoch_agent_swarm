"""HELM centralized secret/config layer — the SINGLE reader of provider credentials.

WHY THIS EXISTS
---------------
Before this module ~15 files read XAI / OPENAI / ANTHROPIC / GEMINI / DEEPSEEK /
OLLAMA credentials directly from os.environ, each re-implementing its own alias
fallbacks (GOOGLE_API_KEY vs GEMINI_API_KEY, OLLAMA_HOST vs OLLAMA_URL, ...). That
sprawl makes the four things HELM needs hard:

    * rotate a key           -> one place, not fifteen
    * audit provider usage   -> ask one component "who is configured?"
    * swap a model/provider  -> the router changes, not every call site
    * multi-env (dev/prod)    -> the config layer selects the source

This is the one place that reads provider credentials from the environment. Every
other component asks SECRETS. It NEVER logs or returns secret material except the
value itself to an authorized caller; audit surfaces get booleans only.

FAIL-CLOSED
-----------
provider_key() returns None when a credential is absent (the caller decides whether
to degrade or raise). require() raises a clear error naming the env vars to set.
Values are read live from os.environ on each call, so a rotated key takes effect on
the next lookup (long-running callers that cache a key still need their own reload).
"""
from __future__ import annotations

import os
from typing import Dict, Optional, Tuple

# Canonical provider -> accepted env var names (first non-empty wins). Aliases are
# centralized here so no call site re-implements the fallback logic.
_PROVIDER_ENV: Dict[str, Tuple[str, ...]] = {
    "xai":        ("XAI_API_KEY", "GROK_API_KEY"),
    "openai":     ("OPENAI_API_KEY",),
    "anthropic":  ("ANTHROPIC_API_KEY",),
    "gemini":     ("GOOGLE_API_KEY", "GEMINI_API_KEY"),
    "deepseek":   ("DEEPSEEK_API_KEY",),
    "elevenlabs": ("ELEVENLABS_API_KEY", "ELEVEN_LABS_API_KEY"),
}

# Provider name aliases callers may pass -> canonical key above.
_ALIASES = {
    "google": "gemini", "google_frontier": "gemini",
    "openai_frontier": "openai", "grok": "xai",
}

_OLLAMA_ENV: Tuple[str, ...] = ("OLLAMA_HOST", "OLLAMA_URL")
_OLLAMA_DEFAULT = "http://127.0.0.1:11434"

# The set of env var names that ARE provider credentials. The ratchet test
# (tests/test_secrets_centralized.py) forbids direct reads of these outside this
# module, so new code cannot re-introduce the sprawl.
PROVIDER_KEY_ENV_NAMES = frozenset(
    name for names in _PROVIDER_ENV.values() for name in names
)


def _first_env(names: Tuple[str, ...]) -> Optional[str]:
    for n in names:
        v = os.environ.get(n)
        if v and v.strip():
            return v.strip()
    return None


class _Secrets:
    """The single credential reader. Instantiated once as SECRETS below."""

    def _canon(self, provider: str) -> str:
        p = (provider or "").lower()
        return _ALIASES.get(p, p)

    def provider_key(self, provider: str) -> Optional[str]:
        """The credential for a provider, or None if unset. Never raises."""
        names = _PROVIDER_ENV.get(self._canon(provider))
        return _first_env(names) if names else None

    def require(self, provider: str) -> str:
        """The credential for a provider, or raise with the env vars to set."""
        v = self.provider_key(provider)
        if not v:
            names = _PROVIDER_ENV.get(self._canon(provider), ())
            raise RuntimeError(
                f"HELM: missing credential for provider {provider!r}. "
                f"Set one of: {', '.join(names) or '(unknown provider)'}"
            )
        return v

    def has(self, provider: str) -> bool:
        return bool(self.provider_key(provider))

    def ollama_url(self) -> str:
        return _first_env(_OLLAMA_ENV) or _OLLAMA_DEFAULT

    def configured_providers(self) -> Dict[str, bool]:
        """Which providers have a credential present — booleans ONLY, never the
        values. Safe for audit UIs and health checks."""
        return {p: self.has(p) for p in _PROVIDER_ENV}


SECRETS = _Secrets()
