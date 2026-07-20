"""governance_manifest.py — the Proof Record: the single definition of a governed decision.

HELM-GOV | extends: NEW module (see justification) | doctrine: Governance-before-Capability
          | edr: EDR-0006-R1 | why: one shared Proof Record schema+validator so the gate (R2),
          | the Evidence Resolver (R3) and dispatch (R4) never grow divergent copies of the shape.

WHY A NEW MODULE (EDR-0006-R10, "extend before create"):
  The Proof Record shape is consumed by THREE callers — governance_engine.govern_decision (N1),
  proof_contract.may_advance_state (Evidence Resolver), and the dispatch emitters (N6). Putting the
  schema in any one of them would force the other two to import it or, worse, re-declare it — the
  exact governance duplication Founder Directive #1 forbids. This module exists specifically to
  REMOVE that duplication: one definition, three callers. It adds no runtime behavior of its own
  (pure schema + validation), so it reduces complexity rather than adding a subsystem.

THE PROOF RECORD (the doctrine's six properties as fields, provable WITHOUT reconstructing logs):
    authorized      {authority, decision_id, gate}          -> Authorized
    explanation     "why this decision, one line"           -> Explained
    trace           {correlation_id, input_digests[]}       -> Traced
    proven          {proof_command, exit_code, evidence_hash}-> Proven
    audit           {record_hash, prev_hash}                -> Audited
    reproducibility {tested_commit, environment}            -> Reproduced
    evidence_class  OBSERVED|DERIVED|CACHED|ASSERTED|UNKNOWN
    governance_state GOVERNED|NEEDS_MIGRATION|UNKNOWN

A record is GOVERNED only when every property block is populated AND evidence_class is advancing
(OBSERVED/DERIVED). Anything else is UNKNOWN for a live decision (fail-closed) — never assumed
complete. "Unknown is preferable to unsupported certainty."
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

# Truth classes that may advance state — mirrors backend/security/proof_contract.py (Evidence
# Doctrine). Kept as plain strings here so this module stays dependency-free (importable by the
# gate, the resolver, and dispatch without cycles).
ADVANCING_CLASSES = frozenset({"OBSERVED", "DERIVED"})
EVIDENCE_CLASSES = frozenset({"OBSERVED", "DERIVED", "CACHED", "ASSERTED", "UNKNOWN"})

# Governance states a live decision may hold.
GOVERNED = "GOVERNED"
NEEDS_MIGRATION = "NEEDS_MIGRATION"
UNKNOWN = "UNKNOWN"

# Legacy classification labels (Phase 2). VERIFIED is deliberately NOT "GOVERNED": legacy artifacts
# are never PROMOTED to GOVERNED without an explicit migration record (EDR-0006 INV-3 / Directive #7).
LEGACY_VERIFIED = "VERIFIED"
LEGACY_NEEDS_MIGRATION = "NEEDS_MIGRATION"
LEGACY_UNKNOWN = "UNKNOWN"

# Provenance of the decision the Proof Record describes. INV-3 is enforced at the GATE (not by caller
# discipline): a LEGACY-sourced record can only reach GOVERNED if it also carries a migration block.
SOURCE_LIVE = "LIVE"
SOURCE_LEGACY = "LEGACY"


def is_legacy_sourced(proof_record: Dict[str, Any]) -> bool:
    return isinstance(proof_record, dict) and proof_record.get("source") == SOURCE_LEGACY


def has_migration_record(proof_record: Dict[str, Any]) -> bool:
    """A migration block must name who/what migrated it and against which evidence — not just a flag."""
    m = proof_record.get("migration") if isinstance(proof_record, dict) else None
    return isinstance(m, dict) and not _is_empty(m.get("migration_ref")) and not _is_empty(m.get("migrated_by"))

# property -> required non-empty sub-fields. This tuple IS the schema.
REQUIRED_PROPERTIES: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("authorized", ("authority", "decision_id", "gate")),   # Authorized
    ("explanation", ()),                                     # Explained (scalar, non-empty)
    ("trace", ("correlation_id", "input_digests")),         # Traced
    ("proven", ("proof_command", "exit_code", "evidence_hash")),  # Proven
    ("audit", ("record_hash",)),                            # Audited (prev_hash may be null at genesis)
    ("reproducibility", ("tested_commit", "environment")),  # Reproduced
)

# Anchors that make a legacy record a MIGRATION candidate rather than pure UNKNOWN: it must at least
# be traceable + auditable (has a correlation_id and a record hash) so a manifest can be back-filled.
MIGRATION_ANCHORS = ("trace", "audit")


def _is_empty(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, str):
        return v.strip() == ""
    if isinstance(v, (list, tuple, dict)):
        return len(v) == 0
    return False  # 0 (e.g. exit_code) and False are legitimately present


def validate(proof_record: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Return (ok, missing_field_paths). The single source of truth for Proof Record completeness.

    ok == True means every required property block is populated. It does NOT by itself mean GOVERNED
    — the caller must also check evidence_class via is_advancing(). Kept separate so the gate can
    report *why* a record is not GOVERNED.
    """
    missing: List[str] = []
    if not isinstance(proof_record, dict):
        return False, ["proof_record:not_a_mapping"]

    for prop, subfields in REQUIRED_PROPERTIES:
        val = proof_record.get(prop)
        if _is_empty(val):
            missing.append(prop)
            continue
        if subfields:
            if not isinstance(val, dict):
                missing.append(f"{prop}:not_a_mapping")
                continue
            for sub in subfields:
                if _is_empty(val.get(sub)):
                    missing.append(f"{prop}.{sub}")

    ec = proof_record.get("evidence_class")
    if ec is None or ec not in EVIDENCE_CLASSES:
        missing.append("evidence_class")

    return (len(missing) == 0, missing)


def is_advancing(proof_record: Dict[str, Any]) -> bool:
    """True when the record's evidence_class may advance state (OBSERVED/DERIVED). Anti-theater:
    ASSERTED/UNKNOWN never advance, so a record full of self-asserted fields cannot be GOVERNED."""
    return proof_record.get("evidence_class") in ADVANCING_CLASSES


def classify_live(proof_record: Dict[str, Any]) -> Tuple[str, List[str]]:
    """Classify a NEW (live) decision. Fail-closed: anything not complete-and-advancing is UNKNOWN.

    Returns (governance_state, missing). GOVERNED requires a complete record with advancing evidence.
    """
    ok, missing = validate(proof_record)
    if ok and is_advancing(proof_record):
        return GOVERNED, []
    return UNKNOWN, missing


def classify_legacy(proof_record: Dict[str, Any]) -> Tuple[str, List[str]]:
    """Classify an EXISTING artifact (Phase 2). Never returns GOVERNED — legacy is promoted to
    GOVERNED only by an explicit migration record (EDR-0006 INV-3).

      VERIFIED         complete + advancing (a full Proof Record is derivable from existing fields)
      NEEDS_MIGRATION  partial, but has trace+audit anchors to back-fill from
      UNKNOWN          insufficient evidence to derive a manifest
    """
    ok, missing = validate(proof_record)
    if ok and is_advancing(proof_record):
        return LEGACY_VERIFIED, []
    has_anchors = all(not _is_empty(proof_record.get(a)) for a in MIGRATION_ANCHORS)
    return (LEGACY_NEEDS_MIGRATION if has_anchors else LEGACY_UNKNOWN), missing


def blank_proof_record() -> Dict[str, Any]:
    """An empty, schema-shaped Proof Record. Helper for emitters; a blank record classifies UNKNOWN."""
    return {
        "authorized": {"authority": "", "decision_id": "", "gate": ""},
        "explanation": "",
        "trace": {"correlation_id": "", "input_digests": []},
        "proven": {"proof_command": "", "exit_code": None, "evidence_hash": ""},
        "audit": {"record_hash": "", "prev_hash": None},
        "reproducibility": {"tested_commit": "", "environment": ""},
        "evidence_class": "UNKNOWN",
        "governance_state": UNKNOWN,
    }
