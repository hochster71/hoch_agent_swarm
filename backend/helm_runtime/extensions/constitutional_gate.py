"""constitutional_gate.py — the EDR-0006 governance gate as a COMPOSED EXTENSION.

HELM-GOV | extends: Governance Engine (frozen core, N1) via composition | edr: EDR-0006-R2
         | why: the single authoritative gate (govern_decision) was previously written IN-PLACE
         | into the frozen file backend/helm_runtime/governance_engine.py (A7 drift finding,
         | 2026-07-19). Per the accepted A7 disposition it now lives here: the frozen core is
         | byte-restored to the verified d8d5139a baseline and callers compose this module.
         | Evidence: coordination/evidence/a7_drift_20260719/ (preserved drift patch + hashes).

Trust boundary:

    Frozen governance engine (validate/authorize — byte-identical to d8d5139a)
            │
            ▼
    THIS versioned extension interface
            │
            ▼
    EDR-0006 decision gate (govern_decision)
            │
            ▼
    Allow / Deny / Hold + evidence

Contract (enforced by design, verified by tests/test_engineering_doctrine.py):
  * FAIL-CLOSED if unavailable: a missing governance_manifest yields UNKNOWN/BLOCKED,
    never an exception into the caller, never GOVERNED.
  * Versioned: EXTENSION_VERSION below; bump on any behavioral change, via EDR.
  * Deterministic + side-effect-free: same Proof Record in, same GovernanceResult out.
  * Evidence-generating: publish_governed_event embeds the Proof Record and its
    record_hash into the event evidence chain.
  * NO SELF-AUTHORIZATION: this module holds no mutable state and cannot alter its
    own authorization status; classification comes only from the supplied record.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass

EXTENSION_VERSION = "1.0.0"
EXTENSION_EDR = "EDR-0006-R2"

try:  # fail-closed availability: without the manifest, nothing can be GOVERNED
    from backend.helm_runtime import governance_manifest as _gm
    _MANIFEST_AVAILABLE = True
except Exception:  # pragma: no cover - degraded environment
    _gm = None  # type: ignore[assignment]
    _MANIFEST_AVAILABLE = False


@dataclass(frozen=True)
class GovernanceResult:
    """Outcome of govern_decision. `may_advance` is the fail-closed answer callers gate on."""
    governance_state: str          # GOVERNED | NEEDS_MIGRATION | UNKNOWN
    may_advance: bool              # True only when GOVERNED
    evidence_class: str            # echoed from the Proof Record (UNKNOWN if absent)
    missing: Tuple[str, ...]       # which Proof Record fields are absent/empty
    reason: str


def govern_decision(proof_record: Optional[Dict[str, Any]], *, legacy: bool = False) -> GovernanceResult:
    """THE authoritative governance gate (EDR-0006-R2). Deterministic, side-effect-free.

    A material decision may advance state only when this returns GOVERNED. For a NEW decision
    (legacy=False) anything not complete-and-advancing is UNKNOWN — fail-closed (INV-2). Legacy
    classification (legacy=True) never returns GOVERNED; that promotion requires an explicit
    migration record (INV-3). Missing/blank record ⇒ UNKNOWN, never assumed complete.
    """
    if not _MANIFEST_AVAILABLE:
        return GovernanceResult(
            governance_state="UNKNOWN", may_advance=False,
            evidence_class="UNKNOWN", missing=("governance_manifest",),
            reason="BLOCKED: governance_manifest unavailable — extension fails closed",
        )
    pr = proof_record if isinstance(proof_record, dict) else None
    if pr is None:
        return GovernanceResult(
            governance_state=_gm.UNKNOWN, may_advance=False,
            evidence_class="UNKNOWN", missing=("proof_record",),
            reason="BLOCKED: no Proof Record attached (fail-closed; unknown over unsupported certainty)",
        )
    ec = str(pr.get("evidence_class") or "UNKNOWN")
    if legacy:
        state, missing = _gm.classify_legacy(pr)
    else:
        state, missing = _gm.classify_live(pr)
    # INV-3 enforced AT THE GATE, not by caller discipline (Auditor finding B5): a LEGACY-sourced
    # record cannot be promoted to GOVERNED unless it carries a migration record — regardless of the
    # `legacy` flag the caller passed. This closes the mis-flag promotion path.
    if state == _gm.GOVERNED and _gm.is_legacy_sourced(pr) and not _gm.has_migration_record(pr):
        state, missing = _gm.NEEDS_MIGRATION, list(missing) + ["migration.migration_ref", "migration.migrated_by"]
    may = state == _gm.GOVERNED
    if may:
        reason = f"GOVERNED: complete Proof Record, {ec} evidence — Authorized/Explained/Traced/Proven/Audited/Reproduced"
    else:
        reason = f"BLOCKED: governance_state={state}; missing={list(missing)}"
    return GovernanceResult(
        governance_state=state, may_advance=may, evidence_class=ec,
        missing=tuple(missing), reason=reason,
    )


def publish_governed_event(*, type: str, producer: str, mission_id: str,
                           correlation_id: Optional[str] = None,
                           evidence: Optional[list] = None,
                           payload: Optional[Dict[str, Any]] = None,
                           mission_version: Optional[int] = None,
                           transaction_id: Optional[str] = None,
                           proof_record: Optional[Dict[str, Any]] = None,
                           path=None):
    """Publish an event WITH a Proof Record through the FROZEN event bus, by composition.

    The frozen Event dataclass (d8d5139a) has no proof_record field — and must not gain one
    in place. This wrapper preserves EDR-0006-R5 semantics compositionally: the Proof Record
    rides in payload["proof_record"] and its record_hash is appended to evidence[], so the
    append-only log remains the governance replay and each event is self-proving.
    NOTE for readers (helm_conmon etc.): accept BOTH the historical top-level "proof_record"
    key (events written while the drifted core was live) and payload["proof_record"].
    """
    from backend.helm_runtime.event_bus import publish_event  # frozen core, unmodified

    ev_refs = list(evidence or [])
    pl = dict(payload or {})
    if proof_record:
        _rh = ((proof_record.get("audit") or {}).get("record_hash")) if isinstance(proof_record, dict) else None
        if _rh and _rh not in ev_refs:
            ev_refs.append(_rh)
        pl["proof_record"] = proof_record
    return publish_event(type=type, producer=producer, mission_id=mission_id,
                         correlation_id=correlation_id, evidence=ev_refs, payload=pl,
                         mission_version=mission_version, transaction_id=transaction_id,
                         path=path)


def proof_encoding_conflict(ev: Dict[str, Any]) -> bool:
    """True when an event carries BOTH proof-record encodings and they disagree.

    Conflicting encodings are an INTEGRITY FINDING — they must fail closed, never be
    merged optimistically (council directive, 2026-07-19)."""
    if not isinstance(ev, dict):
        return False
    top = ev.get("proof_record")
    pl = (ev.get("payload") or {}).get("proof_record")
    return top is not None and pl is not None and top != pl


def event_proof_record(ev: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract an event's Proof Record, accepting both encodings (see publish_governed_event).

    FAIL-CLOSED rules: a malformed record (non-dict) is None; CONFLICTING encodings
    (both present, unequal) are None — an event with an ambiguous proof proves nothing.
    Use proof_encoding_conflict() to surface the conflict as an explicit finding."""
    if not isinstance(ev, dict):
        return None
    if proof_encoding_conflict(ev):
        return None
    pr = ev.get("proof_record")
    if pr is None:
        pr = (ev.get("payload") or {}).get("proof_record")
    return pr if isinstance(pr, dict) else None
