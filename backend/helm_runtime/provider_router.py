"""Provider Router — workers are replaceable plugins.

Roles are durable (orchestrator / builder / auditor). The *provider+model* bound
to each role is not. This router resolves a role to its current binding from
coordination/governance/role_bindings.json, so replacing GPT-5.6 with GPT-6, or
Claude with a successor, is a one-line binding change — never an architecture
rewrite.

SECRET DISCIPLINE: this module NEVER reads, prints, or returns a secret value.
It only reports whether the expected API-key environment variable is *present*,
so the runtime can tell an operational worker from an unconfigured one without
ever touching the key itself.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.helm_runtime.governance_engine import normalize_role

ROOT = Path(__file__).resolve().parents[2]
BINDINGS_PATH = ROOT / "coordination" / "governance" / "role_bindings.json"

# Which env var carries each provider's credential. We check presence only.
PROVIDER_KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "xai": "XAI_API_KEY",
    "google": "GEMINI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "local": None,  # local provider needs no cloud key
}

VALID_ROLES = ("orchestrator", "builder", "auditor")


def _load_bindings(path: Path = BINDINGS_PATH) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_worker(role: str, *, path: Path = BINDINGS_PATH) -> Dict[str, Any]:
    """Resolve a role to its current worker binding.

    Returns a dict with provider, model, display_name, overlay, key_present
    (bool), and configured (bool). Never returns the key itself.
    """
    r = normalize_role(role)
    if r not in VALID_ROLES:
        return {
            "role": r,
            "error": "NOT_A_BINDABLE_ROLE",
            "note": "Only orchestrator/builder/auditor bind to providers; "
            "founder is human; Runtime/Truth are platform, not actors.",
            "configured": False,
        }
    bindings = (_load_bindings(path).get("role_bindings") or {}).get(r) or {}
    provider = (bindings.get("provider") or "").lower()
    key_env = PROVIDER_KEY_ENV.get(provider, None)
    key_present = True if provider == "local" else bool(key_env and os.environ.get(key_env))
    return {
        "role": r,
        "provider": provider or None,
        "model": bindings.get("model"),
        "mode": bindings.get("mode"),
        "display_name": bindings.get("display_name"),
        "overlay": bindings.get("overlay"),
        "key_env": key_env,
        "key_present": key_present,
        # A worker is "configured" when bound AND its credential is available.
        "configured": bool(provider) and key_present,
    }


def list_workers(*, path: Path = BINDINGS_PATH) -> List[Dict[str, Any]]:
    """All three role bindings with configured/key-presence status (no secrets)."""
    return [resolve_worker(r, path=path) for r in VALID_ROLES]


def worker_health(*, path: Path = BINDINGS_PATH) -> Dict[str, Any]:
    """Projection: how many workers are actually configured to run right now."""
    workers = list_workers(path=path)
    configured = [w for w in workers if w.get("configured")]
    return {
        "engine": "provider_router",
        "is_actor": False,
        "total_roles": len(workers),
        "configured_count": len(configured),
        "unconfigured": [
            {"role": w["role"], "provider": w.get("provider"), "reason": "missing_key"}
            for w in workers
            if not w.get("configured")
        ],
        "workers": workers,
    }
