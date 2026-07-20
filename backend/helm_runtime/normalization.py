"""EDR-0003 Normalization Layer — canonical record shapes for HELM runtime.

Implements EDR-0003 (`docs/helm/edr/EDR-0003-normalization.md`) as code. This
module changes **no architecture**: it imports only the frozen read-surfaces of
the runtime and produces the single canonical shape each record type must take.
It is the executable answer to the four normalization fixes:

  N2 — one canonical ``/mission`` shape. :func:`normalize_mission_view` is the
       single source of truth for the mission projection. Any producer (the
       bridge projection, the legacy ``helm_live_api`` route, a raw on-disk
       mission doc) is folded into the same field set, so callers never branch
       on which route answered. ``mission_version`` is always present.

  N3 — Constitutional names are canonical; code names are aliases. The alias
       table lives here (:data:`TERMINOLOGY_ALIASES`) with lookups both ways,
       so the doc table and the code agree by construction.

  N4 — the verification target hashes **implementation only**. EDRs and reports
       *reference* the id, they never contribute to it.
       :func:`is_implementation_path` / :func:`hash_implementation` encode that
       rule so an id cannot fork because prose was edited.

Non-goal (per EDR-0003): no engine, interface, or principle change. This layer
is pure/​derived — it never writes the mission and holds no state.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# --------------------------------------------------------------------------- #
# N2 — canonical mission projection shape
# --------------------------------------------------------------------------- #

# The single canonical field set for GET /api/v1/helm/mission. Kept byte-for-
# byte aligned with the frozen bridge projection (bridge_api._mission_view) so
# there is exactly one mission shape across every producer (EDR-0003 N2).
CANONICAL_MISSION_FIELDS: Tuple[str, ...] = (
    "mission_version",
    "transaction_id",
    "state",
    "operational_status",
    "mission",
    "critical_path",
    "external_gates",
    "projection_hint",
    "occ_note",
)

_OCC_NOTE = "PATCH must send expected_parent_version = this mission_version"

# Legacy/alternate keys some producers emit → the canonical key they map to.
# Only used to fold non-canonical records; canonical keys always win.
_MISSION_KEY_ALIASES: Dict[str, str] = {
    "version": "mission_version",
    "tx_id": "transaction_id",
    "transactionId": "transaction_id",
    "status": "operational_status",
    "criticalPath": "critical_path",
    "gates": "external_gates",
    "externalGates": "external_gates",
}


def normalize_mission_view(
    doc: Optional[Dict[str, Any]],
    *,
    hint: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Fold any mission record into the one canonical ``/mission`` shape.

    ``doc`` is a raw mission document (e.g. from ``mission_store.read_mission``)
    or any producer's mission dict. ``hint`` is the projection hint
    (``mission_runtime.mission_projection_hint``); if omitted it is read from
    the record's own ``projection_hint`` when present, else ``None``.

    The result always has exactly :data:`CANONICAL_MISSION_FIELDS` keys, missing
    values filled with ``None``. ``mission_version`` is always present (the N2
    regression invariant) — ``None`` when the mission is absent, never dropped.
    """
    src: Dict[str, Any] = dict(doc or {})
    # Fold recognised legacy keys in without letting them shadow canonical keys.
    for legacy, canonical in _MISSION_KEY_ALIASES.items():
        if legacy in src and canonical not in src:
            src[canonical] = src[legacy]

    view = {field: src.get(field) for field in CANONICAL_MISSION_FIELDS}
    if hint is not None:
        view["projection_hint"] = hint
    view["occ_note"] = _OCC_NOTE
    return view


def mission_shape_ok(view: Dict[str, Any]) -> bool:
    """True iff ``view`` is exactly the canonical mission shape (N2 invariant)."""
    return set(view.keys()) == set(CANONICAL_MISSION_FIELDS) and "mission_version" in view


# --------------------------------------------------------------------------- #
# N3 — terminology alias table (Constitutional names canonical)
# --------------------------------------------------------------------------- #

# Each entry: the Constitutional (canonical) name, and the code artefacts that
# are aliases of it. This is the executable form of the Normalization Register
# alias table so the doc and the code cannot drift.
TERMINOLOGY_ALIASES: Tuple[Dict[str, Any], ...] = (
    {
        "constitutional": "Provider Registry",
        "code_aliases": ("provider_router.py", "role_bindings.json"),
        "kind": "registry",
    },
    {
        "constitutional": "Runtime Truth Engine",
        "code_aliases": ("truth_engine.py", "backend/truth/*"),
        "kind": "engine",
    },
    {
        "constitutional": "Worker Registry",
        "code_aliases": ("role_bindings", "worker_role_health"),
        "kind": "registry",
    },
)


def alias_table() -> List[Dict[str, Any]]:
    """The N3 alias table as a plain list (for docs/UI/JSON emission)."""
    return [
        {
            "constitutional": e["constitutional"],
            "code_aliases": list(e["code_aliases"]),
            "kind": e["kind"],
        }
        for e in TERMINOLOGY_ALIASES
    ]


def constitutional_name(alias: str) -> Optional[str]:
    """Resolve a code alias to its Constitutional name, or None if unknown."""
    a = (alias or "").strip()
    for e in TERMINOLOGY_ALIASES:
        if a == e["constitutional"] or a in e["code_aliases"]:
            return e["constitutional"]
    return None


def code_aliases(constitutional: str) -> List[str]:
    """Return the code aliases for a Constitutional name (empty if unknown)."""
    name = (constitutional or "").strip()
    for e in TERMINOLOGY_ALIASES:
        if name == e["constitutional"]:
            return list(e["code_aliases"])
    return []


# --------------------------------------------------------------------------- #
# Dispatch / worker / provider record normalization
# --------------------------------------------------------------------------- #

CANONICAL_WORKER_FIELDS: Tuple[str, ...] = (
    "role",
    "binding",
    "model",
    "display_name",
    "configured",
    "reachable",
    "dispatch_enabled",
    "status",
    "reason",
)


def normalize_worker_record(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Fold a worker/role-health record into the canonical worker shape.

    Accepts either a ``dispatch_gateway.worker_role_health`` row or a
    ``provider_router.resolve_worker`` binding (which uses ``provider`` rather
    than ``binding``). Booleans are coerced; ``status`` is derived from
    ``dispatch_enabled`` when the producer did not set it.
    """
    src: Dict[str, Any] = dict(raw or {})
    binding = src.get("binding")
    if binding is None:
        prov = src.get("provider")
        binding = (prov or None) if prov else None

    configured = bool(src.get("configured"))
    dispatch_enabled = bool(src.get("dispatch_enabled"))
    reachable = bool(src.get("reachable"))
    status = src.get("status")
    if status not in ("AVAILABLE", "BLOCKED"):
        status = "AVAILABLE" if dispatch_enabled else "BLOCKED"

    return {
        "role": src.get("role"),
        "binding": binding,
        "model": src.get("model"),
        "display_name": src.get("display_name"),
        "configured": configured,
        "reachable": reachable,
        "dispatch_enabled": dispatch_enabled,
        "status": status,
        "reason": src.get("reason"),
    }


CANONICAL_PROVIDER_FIELDS: Tuple[str, ...] = (
    "provider",
    "configured",
    "status",
    "reason",
    "dispatch_implemented",
)


def normalize_provider_health(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Fold a provider adapter health record into the canonical provider shape."""
    src: Dict[str, Any] = dict(raw or {})
    configured = bool(src.get("configured"))
    status = src.get("status")
    if status not in ("READY", "BLOCKED"):
        status = "READY" if configured else "BLOCKED"
    return {
        "provider": src.get("provider"),
        "configured": configured,
        "status": status,
        "reason": src.get("reason"),
        "dispatch_implemented": bool(src.get("dispatch_implemented")),
    }


CANONICAL_DISPATCH_FIELDS: Tuple[str, ...] = (
    "role",
    "capability",
    "provider",
    "outcome",
    "reason",
    "correlation_id",
)

_VALID_OUTCOMES = ("dispatched", "blocked", "error")


def normalize_dispatch_record(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Fold a dispatch attempt/result record into the canonical dispatch shape.

    ``outcome`` is one of ``dispatched`` / ``blocked`` / ``error``. Unknown or
    missing outcomes normalize to ``blocked`` (fail-closed: an unrecognised
    dispatch record is treated as not-dispatched, never as success).
    """
    src: Dict[str, Any] = dict(raw or {})
    outcome = src.get("outcome")
    if outcome not in _VALID_OUTCOMES:
        outcome = "blocked"
    provider = src.get("provider")
    if isinstance(provider, str):
        provider = provider.lower() or None
    return {
        "role": src.get("role"),
        "capability": src.get("capability"),
        "provider": provider,
        "outcome": outcome,
        "reason": src.get("reason"),
        "correlation_id": src.get("correlation_id"),
    }


# --------------------------------------------------------------------------- #
# N4 — verification target hashing (implementation only)
# --------------------------------------------------------------------------- #

# Path fragments that are documentation/evidence, never implementation. A path
# under any of these is EXCLUDED from the verification target id so editing an
# EDR or a report cannot fork the id (EDR-0003 N4).
_NON_IMPLEMENTATION_MARKERS: Tuple[str, ...] = (
    "docs/helm/edr/",
    "docs/evidence/",
    "docs/helm/",
    "/reports/",
    "README",
)

_NON_IMPLEMENTATION_SUFFIXES: Tuple[str, ...] = (".md", ".rst", ".txt")


def is_implementation_path(path: str) -> bool:
    """True iff ``path`` is implementation (code/config/tests), not doc/report.

    Only implementation paths contribute to the verification target id. EDRs,
    conformance reports, and other prose reference the id but never feed it.
    """
    p = str(path).replace("\\", "/")
    lower = p.lower()
    if any(lower.endswith(sfx) for sfx in _NON_IMPLEMENTATION_SUFFIXES):
        return False
    if any(marker.lower() in lower for marker in _NON_IMPLEMENTATION_MARKERS):
        return False
    return True


def hash_implementation(
    files: Iterable[Tuple[str, bytes]],
) -> str:
    """Deterministic sha256 over implementation files only (EDR-0003 N4).

    ``files`` is an iterable of ``(relative_path, contents_bytes)``. Non-
    implementation paths are filtered out via :func:`is_implementation_path`,
    the survivors are sorted by path, and each contributes
    ``path\\n<sha256(contents)>\\n`` to a rolling digest. The id is therefore
    stable across any doc/EDR/report edit and changes only when implementation
    changes.
    """
    impl = sorted(
        ((p, b) for (p, b) in files if is_implementation_path(p)),
        key=lambda pb: pb[0].replace("\\", "/"),
    )
    roll = hashlib.sha256()
    for path, content in impl:
        norm_path = str(path).replace("\\", "/")
        roll.update(norm_path.encode("utf-8"))
        roll.update(b"\n")
        roll.update(hashlib.sha256(content).hexdigest().encode("ascii"))
        roll.update(b"\n")
    return roll.hexdigest()


def hash_implementation_paths(root: Path, paths: Iterable[str]) -> str:
    """Convenience wrapper: read ``paths`` under ``root`` and hash implementation.

    Missing files are skipped (they contribute nothing) rather than raising, so
    the id reflects what is present. Non-implementation paths are filtered by
    :func:`hash_implementation`.
    """
    loaded: List[Tuple[str, bytes]] = []
    for rel in paths:
        fp = root / rel
        if fp.exists() and fp.is_file():
            loaded.append((rel, fp.read_bytes()))
    return hash_implementation(loaded)
