"""Capability Registry — route by capability, not by brand.

A task declares the capability it needs (e.g. "python", "red_team"); the runtime
maps that to a role via this registry, then provider_router resolves the current
model binding. Replacing a provider never touches routing logic.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "coordination" / "governance" / "capability_registry.json"


def _load(path: Path = REGISTRY_PATH) -> Dict[str, Any]:
    if not path.exists():
        return {"roles": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def capabilities_for_role(role: str, *, path: Path = REGISTRY_PATH) -> List[str]:
    return list(((_load(path).get("roles") or {}).get(role) or {}).get("capabilities") or [])


def roles_for_capability(capability: str, *, path: Path = REGISTRY_PATH) -> List[str]:
    """Which role(s) advertise a capability. Case-insensitive exact match."""
    cap = (capability or "").strip().lower()
    out: List[str] = []
    for role, spec in (_load(path).get("roles") or {}).items():
        caps = [c.lower() for c in (spec.get("capabilities") or [])]
        if cap in caps:
            out.append(role)
    return out


def route_capability(capability: str, *, path: Path = REGISTRY_PATH) -> Dict[str, Any]:
    """Resolve a capability to the role that should handle it (no provider call)."""
    roles = roles_for_capability(capability, path=path)
    if not roles:
        return {"capability": capability, "resolved": False, "reason": "no role advertises this capability"}
    return {"capability": capability, "resolved": True, "role": roles[0], "all_roles": roles}


def all_capabilities(*, path: Path = REGISTRY_PATH) -> Dict[str, List[str]]:
    return {role: (spec.get("capabilities") or []) for role, spec in (_load(path).get("roles") or {}).items()}
