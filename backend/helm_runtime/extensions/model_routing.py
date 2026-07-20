"""model_routing.py — mutable, governed model-binding registry (A7 remediation, 2026-07-19).

HELM-GOV | extends: role bindings (frozen governance surface) via composition
         | why: the builder→claude-sonnet-5 rebinding was written IN-PLACE into the frozen
         | coordination/governance/role_bindings.json (A7 drift). Model bindings are MUTABLE
         | OPERATIONAL CONFIGURATION and are expected to evolve — they must never require
         | changing a frozen constitutional artifact. They now live in the versioned registry
         | coordination/model_routing/role_bindings.json; the frozen file remains the
         | constitutional fallback and is validated, not edited.

resolve_binding(role) precedence:
  1. ACTIVE entry for the role in coordination/model_routing/role_bindings.json
     (must carry effective_at / authorized_by / change_record — otherwise it is
     IGNORED, fail-closed to the constitutional fallback)
  2. the frozen coordination/governance/role_bindings.json entry
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

EXTENSION_VERSION = "1.0.0"

_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = _ROOT / "coordination" / "model_routing" / "role_bindings.json"
FROZEN_FALLBACK_PATH = _ROOT / "coordination" / "governance" / "role_bindings.json"

_REQUIRED_FIELDS = ("role", "provider", "model", "effective_at", "authorized_by", "change_record", "status")


def _load(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _registry_entry_state(role: str) -> tuple:
    """(binding_or_None, state) where state ∈ ABSENT | REJECTED | INACTIVE | ACTIVE_OK.
    REJECTED = an entry exists for the role but is malformed/under-attributed/unauthorized —
    it must be surfaced as MUTABLE_REGISTRY_REJECTED, not silently treated as absent."""
    reg = _load(REGISTRY_PATH)
    if reg is None:
        # missing file OR malformed JSON — malformed is a rejection, absent is absent
        return (None, "REJECTED") if REGISTRY_PATH.exists() else (None, "ABSENT")
    found_any = False
    for b in reg.get("bindings", []) or []:
        if not isinstance(b, dict) or b.get("role") != role:
            continue
        found_any = True
        if b.get("status") != "ACTIVE":
            continue
        if any(not b.get(f) for f in _REQUIRED_FIELDS):
            return None, "REJECTED"  # under-attributed mutable config: never trusted
        return b, "ACTIVE_OK"
    return (None, "INACTIVE") if found_any else (None, "ABSENT")


def registry_binding(role: str) -> Optional[Dict[str, Any]]:
    """Return the ACTIVE, fully-attributed registry binding for role, else None (fail-closed)."""
    b, state = _registry_entry_state(role)
    return b if state == "ACTIVE_OK" else None


def list_roles() -> list:
    """All known roles: frozen constitutional bindings + ACTIVE fully-attributed registry roles."""
    roles = set()
    frozen = _load(FROZEN_FALLBACK_PATH) or {}
    roles.update((frozen.get("role_bindings") or {}).keys())
    reg = _load(REGISTRY_PATH) or {}
    for b in reg.get("bindings", []) or []:
        if isinstance(b, dict) and b.get("status") == "ACTIVE" and b.get("role"):
            roles.add(b["role"])
    return sorted(roles)


def binding_status(role: str) -> Dict[str, Any]:
    """Runtime telemetry record for the effective binding (council directive: emit the
    effective binding source and WARN when frozen and external bindings disagree —
    finding ROUTING-REGISTRY-DUAL-READ)."""
    reg, reg_state = _registry_entry_state(role)
    frozen = _load(FROZEN_FALLBACK_PATH) or {}
    fb = (frozen.get("role_bindings") or {}).get(role) or {}
    effective = reg if reg is not None else ({**fb, "role": role} if fb else None)
    # bindings_disagree is meaningful ONLY when an authorized registry value exists to compare;
    # on rejection it is None (council directive) — the salient fact is the rejection itself.
    disagree = (bool(reg.get("model") != fb.get("model")) if (reg and fb) else
                (None if reg_state == "REJECTED" else False))
    if reg is not None:
        warning = ("DUAL-READ NOTE: registry and frozen bindings disagree — expected while the "
                   "mutable registry is authorized and the frozen value is the constitutional "
                   "fallback; both values reported here (finding ROUTING-REGISTRY-DUAL-READ)"
                   if disagree else None)
    elif reg_state == "REJECTED":
        warning = "MUTABLE_REGISTRY_REJECTED"
    else:
        warning = None
    return {
        "role": role,
        "effective_model": (effective or {}).get("model", "UNKNOWN"),
        "effective_source": ("mutable_registry" if reg is not None
                             else ("frozen_constitutional_fallback" if fb else "UNRESOLVED")),
        "binding_source": ("coordination/model_routing/role_bindings.json" if reg is not None
                           else ("coordination/governance/role_bindings.json (frozen fallback)" if fb
                                 else "UNRESOLVED")),
        "registry_model": (reg or {}).get("model"),
        "registry_entry_state": reg_state,        # ABSENT | REJECTED | INACTIVE | ACTIVE_OK
        "frozen_fallback_model": fb.get("model"),
        "registry_authorized": reg is not None,   # ACTIVE + fully attributed, else False
        "fallback_used": reg is None and bool(fb),
        "fallback_available": bool(fb),
        "registry_version": EXTENSION_VERSION,
        "change_record": (reg or {}).get("change_record"),
        "bindings_disagree": disagree,
        "warning": warning,
    }


def resolve_binding(role: str) -> Dict[str, Any]:
    """Effective binding for a role: governed mutable registry first, frozen fallback second.

    Always returns a dict with at least provider/model/source; UNKNOWN if neither source
    resolves (fail-closed — callers must treat UNKNOWN as not-dispatchable).
    """
    b = registry_binding(role)
    if b is not None:
        return {**b, "source": "model_routing_registry"}
    frozen = _load(FROZEN_FALLBACK_PATH) or {}
    fb = (frozen.get("role_bindings") or {}).get(role)
    if isinstance(fb, dict):
        return {**fb, "role": role, "source": "frozen_constitutional_fallback"}
    return {"role": role, "provider": "UNKNOWN", "model": "UNKNOWN", "source": "UNRESOLVED"}
