"""proof_contract.py — HELM evidence doctrine, enforced in code (not prose).

FOUNDER-RATIFIED GOVERNING RULE
-------------------------------
    NO CLAIM MAY ADVANCE STATE.
    ONLY FRESH, MACHINE-VERIFIABLE EVIDENCE MAY ADVANCE STATE.

This module is the behavioral layer HELM was missing. It makes the four enforcement
controls executable:

  PROOF-CONTRACT-001   a task cannot become READY without a complete proof contract
  NO-SUBSTITUTION-001  a missing mechanism yields a TYPED BLOCKER, never a workaround
  FRESH-EVIDENCE-001   a PASS expires when its evidence exceeds its freshness window
  NEGATIVE-CONTROL-001 a high-assurance validator must prove it can reject a broken state

Truth classification (only OBSERVED / valid DERIVED may advance a critical node):
  OBSERVED   produced by a current command, API call, or runtime event
  DERIVED    mechanically computed from OBSERVED evidence
  CACHED     previously OBSERVED but outside the active freshness window
  ASSERTED   supplied by a model, operator, or static file without independent proof
  UNKNOWN    no reliable evidence exists
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Truth(str, Enum):
    OBSERVED = "OBSERVED"
    DERIVED = "DERIVED"
    CACHED = "CACHED"
    ASSERTED = "ASSERTED"
    UNKNOWN = "UNKNOWN"


# Only these may move a critical PERT node forward.
ADVANCING = frozenset({Truth.OBSERVED, Truth.DERIVED})

REQUIRED_CONTRACT_FIELDS = (
    "goal",              # observable end state
    "mechanism",         # permitted implementation path
    "proof_command",     # machine-executable verification
    "expected_result",   # binary success condition
    "constraints",       # forbidden actions / security boundaries
    "failure_behavior",  # must be BLOCKED or FAILED, never substitute
)


class ProofContractError(ValueError):
    """Raised when a task tries to become executable without a valid proof contract."""


@dataclass(frozen=True)
class ProofContract:
    goal: str
    mechanism: str
    proof_command: str
    expected_result: str
    constraints: tuple[str, ...]
    failure_behavior: str
    freshness_window_seconds: int = 300

    @staticmethod
    def validate(d: dict[str, Any]) -> "ProofContract":
        """PROOF-CONTRACT-001. A task cannot become READY unless this passes."""
        missing = [f for f in REQUIRED_CONTRACT_FIELDS if not d.get(f)]
        if missing:
            raise ProofContractError(f"incomplete proof contract; missing/empty: {missing}")

        fb = str(d["failure_behavior"]).upper()
        # NO-SUBSTITUTION-001: the only permitted failure behaviors are typed blockers.
        if not any(tok in fb for tok in ("BLOCK", "FAIL")):
            raise ProofContractError(
                f"failure_behavior must return a typed blocker (BLOCKED/FAILED); got {d['failure_behavior']!r}"
            )
        if "SUBSTIT" in fb or "WORKAROUND" in fb or "INFER" in fb:
            raise ProofContractError("failure_behavior must not permit substitution/inference")

        cons = d["constraints"]
        cons_t = tuple(cons) if isinstance(cons, (list, tuple)) else (str(cons),)

        fw = int(d.get("freshness_window_seconds", 300))
        if fw <= 0:
            raise ProofContractError("freshness_window_seconds must be > 0")

        return ProofContract(
            goal=str(d["goal"]),
            mechanism=str(d["mechanism"]),
            proof_command=str(d["proof_command"]),
            expected_result=str(d["expected_result"]),
            constraints=cons_t,
            failure_behavior=fb,
            freshness_window_seconds=fw,
        )


@dataclass
class Evidence:
    """A claim plus its provenance. Classification + freshness decide if it may advance."""
    classification: Truth
    observed_at: float                       # epoch seconds
    proof_command: str = ""
    exit_code: int | None = None
    sanitized_output: str = ""               # never raw secrets — run through redact_evidence
    raw_evidence_sha256: str = ""            # hash of the restricted raw log
    tested_commit: str = ""
    environment: str = ""
    positive_control_passed: bool | None = None   # POSITIVE-CONTROL-001: accepts known-good
    negative_control_passed: bool | None = None   # NEGATIVE-CONTROL-001: rejects known-bad
    extra: dict[str, Any] = field(default_factory=dict)

    def age_seconds(self, now: float | None = None) -> float:
        return (now if now is not None else time.time()) - self.observed_at

    def is_fresh(self, window_seconds: int, now: float | None = None) -> bool:
        return self.age_seconds(now) <= window_seconds

    def effective_class(self, window_seconds: int, now: float | None = None) -> Truth:
        """FRESH-EVIDENCE-001: OBSERVED/DERIVED that has aged out becomes CACHED."""
        if self.classification in ADVANCING and not self.is_fresh(window_seconds, now):
            return Truth.CACHED
        return self.classification


def may_advance_state(
    ev: Evidence,
    contract: ProofContract,
    *,
    require_negative_control: bool = True,
    now: float | None = None,
    proof_record: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    """THE governing rule, executable.

    Returns (allowed, reason). A HELM node may only move forward when this returns True.

    HELM-GOV | extends: Evidence Resolver (this fn) | doctrine: Governance-before-Capability
             | edr: EDR-0006-R3 | why: when a Proof Record is supplied, the governance decision is
             | DELEGATED to the single gate governance_engine.govern_decision — this module keeps
             | the evidence basis (freshness/controls) but never re-implements governance. When
             | proof_record is None, behavior is byte-for-byte the pre-doctrine path (backward compat).
    """
    eff = ev.effective_class(contract.freshness_window_seconds, now)

    if eff not in ADVANCING:
        return False, (
            f"BLOCKED: evidence is {eff.value} (was {ev.classification.value}); "
            f"only OBSERVED/DERIVED within {contract.freshness_window_seconds}s may advance state"
        )
    if not ev.proof_command:
        return False, "BLOCKED: no proof_command recorded"
    if ev.exit_code is None:
        return False, "BLOCKED: no exit_code recorded"
    if not ev.raw_evidence_sha256:
        return False, "BLOCKED: no hash of raw evidence recorded (unverifiable provenance)"
    if not ev.tested_commit:
        return False, "BLOCKED: no tested_commit recorded (stale-binding risk)"
    # POSITIVE + NEGATIVE control (a validator must prove BOTH accept-truth and reject-falsehood)
    if require_negative_control:
        if ev.positive_control_passed is not True:
            return False, "BLOCKED: positive control not proven (validator never shown to accept a known-good state)"
        if ev.negative_control_passed is not True:
            return False, "BLOCKED: negative control not proven (validator never shown to reject a broken state)"

    # EDR-0006-R3: if this advance is a governed decision, the governance verdict is delegated to
    # the ONE gate — not re-decided here. Evidence basis above stays authoritative for the facts.
    if proof_record is not None:
        from backend.helm_runtime.extensions.constitutional_gate import govern_decision  # lazy: avoid load-order coupling

        gov = govern_decision(proof_record)
        if not gov.may_advance:
            return False, f"BLOCKED (governance): {gov.reason}"
        return True, (
            f"ADVANCE: {eff.value} evidence, fresh, complete, negative-control proven; "
            f"GOVERNED (missing=none, {gov.evidence_class})"
        )

    return True, f"ADVANCE: {eff.value} evidence, fresh, complete, negative-control proven"


# ── CONTROL-PROOF MATRIX (founder-ratified) ──────────────────────────────────
# "A control is not proven because it exists in code. A control is proven only when
#  all eight conditions hold." This encodes that rule so a validator cannot self-certify.
MATRIX_CONDITIONS = (
    "positive",     # 1. known-good case passes
    "negative",     # 2. known-bad case fails
    "boundary",     # 3. threshold behaves correctly (off-by-one caught)
    "mutation",     # 4. corruption of the protected artifact is detected
    "replay",       # 5. old evidence cannot be reused as fresh proof
    "freshness",    # 6. evidence is within its window
    "provenance",   # 7. bound to commit + environment + artifact digest
    "reproducible", # 8. re-running the proof yields the same result
)


def control_proof_status(matrix: dict[str, bool]) -> tuple[str, list[str]]:
    """Return ('PROVEN'|'PARTIAL'|'DECLARED', missing_conditions).

    PROVEN   = all 8 conditions true
    PARTIAL  = at least positive+negative, but not all 8
    DECLARED = missing positive or negative (i.e. not yet a real control)
    """
    missing = [c for c in MATRIX_CONDITIONS if not matrix.get(c)]
    if not missing:
        return "PROVEN", []
    if matrix.get("positive") and matrix.get("negative"):
        return "PARTIAL", missing
    return "DECLARED", missing
