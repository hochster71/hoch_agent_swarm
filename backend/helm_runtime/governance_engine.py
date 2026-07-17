"""Governance Engine — founder gates, field ownership, constitutional checks.

Does not implement product features. Does not own truth.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
OWNERSHIP_PATH = ROOT / "coordination" / "governance" / "field_ownership.json"

FOUNDER_ONLY_FIELD_PREFIXES = (
    "authorization.",
    "founder_decisions.",
    "secrets_provisioning",
    "deploy_production",
    "publish_external",
    "money_movement",
    "external_submissions",
    "legal_acceptance",
    "organizational_direction",
    "charter_ratification",
)

# Platform engines may write versioning/metadata; actors may not forge truth projections.
PLATFORM_ONLY_PREFIXES = (
    "projections.",
    "mission_version",
    "transaction_id",
    "parent_version",
)


def _load_json(path: Path) -> Dict[str, Any]:
    import json

    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_role(role: str) -> str:
    key = (role or "").strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "chatgpt": "orchestrator",
        "chatgpt_agent": "orchestrator",
        "chief_of_staff": "orchestrator",
        "orchestrator": "orchestrator",
        "claude": "builder",
        "builder": "builder",
        "engineering": "builder",
        "grok": "auditor",
        "auditor": "auditor",
        "assurance": "auditor",
        "founder": "founder",
        "michael": "founder",
        # Explicitly NOT roles:
        "truth": "INVALID_TRUTH_IS_NOT_A_ROLE",
        "runtime": "INVALID_RUNTIME_IS_PLATFORM",
    }
    return aliases.get(key, key)


def is_founder_gate_field(field_path: str) -> bool:
    return any(
        field_path == p.rstrip(".")
        or field_path.startswith(p)
        for p in FOUNDER_ONLY_FIELD_PREFIXES
    )


def role_may_write(role: str, field_path: str, ownership: Optional[Dict[str, Any]] = None) -> bool:
    r = normalize_role(role)
    if r.startswith("INVALID_"):
        return False
    if field_path.startswith(PLATFORM_ONLY_PREFIXES) and r not in ("founder",):
        # platform fields only written by engines via transaction commit path
        return False
    ownership = ownership or _load_json(OWNERSHIP_PATH)
    spec = (ownership.get("roles") or {}).get(r) or {}
    allowed: List[str] = list(spec.get("may_write") or [])
    if field_path == "last_writes" and allowed:
        return True
    for pattern in allowed:
        if pattern.endswith(".*"):
            prefix = pattern[:-2]
            if field_path == prefix or field_path.startswith(prefix + "."):
                return True
        elif pattern.endswith("*"):
            if field_path.startswith(pattern[:-1]):
                return True
        elif field_path == pattern or field_path.startswith(pattern + "."):
            return True
    return False


def validate_proposal(
    role: str,
    patch: Dict[str, Any],
    *,
    ownership: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, List[str]]:
    """Validate actor patch keys (dot paths) against ownership. Founder gates require founder."""
    errors: List[str] = []
    r = normalize_role(role)
    if r.startswith("INVALID_"):
        return False, [f"invalid role: {role!r} (Runtime/Truth are not actor roles)"]
    for field_path in patch.keys():
        if is_founder_gate_field(field_path) and r != "founder":
            errors.append(f"founder gate field requires founder: {field_path}")
            continue
        if not role_may_write(r, field_path, ownership):
            errors.append(f"role {r!r} may not write {field_path!r}")
    return (len(errors) == 0, errors)


def authorize(
    role: str,
    patch: Dict[str, Any],
    *,
    founder_token_present: bool = False,
) -> Tuple[bool, str]:
    """Authorize after validate. Founder-gate fields need founder + token flag (caller supplies)."""
    ok, errs = validate_proposal(role, patch)
    if not ok:
        return False, "; ".join(errs)
    r = normalize_role(role)
    if any(is_founder_gate_field(k) for k in patch) and r == "founder" and not founder_token_present:
        return False, "founder gate requires explicit founder authorization token/session"
    return True, "authorized"
