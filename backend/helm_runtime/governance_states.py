"""governance_states.py — executable governance doctrine.

Converts the PROC-001 review doctrine from prose into enforced types. Every rule here
exists because it was violated during that review, usually by the builder.

    Specified -> Configured -> Enforced -> Sustained -> Validated
    ObservedPresent | ObservedAbsent | Unobserved

DESIGN RULE, inherited from mission_envelope: there is NO setter for lifecycle state.
A control's state is DERIVED from the evidence attached to it. A caller cannot declare
`Validated` — it must supply evidence that discharges the obligation, or the claim
collapses to the highest state the evidence actually supports.

See docs/helm/HELM_EVIDENCE_VS_ENFORCEMENT_DOCTRINE.md (PROPOSED, unratified).
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Sequence


class Epistemic(str, Enum):
    """What the evidence permits concluding. 'Not observed' != 'observed absent'."""
    OBSERVED_PRESENT = "OBSERVED_PRESENT"
    OBSERVED_ABSENT = "OBSERVED_ABSENT"
    UNOBSERVED = "UNOBSERVED"      # no examination occurred -> UNKNOWN, never False

    @property
    def is_known(self) -> bool:
        return self is not Epistemic.UNOBSERVED


class Lifecycle(str, Enum):
    """How far a control has advanced. Ordered; each state has an evidence obligation."""
    UNKNOWN = "UNKNOWN"
    SPECIFIED = "SPECIFIED"        # described in a design artifact
    CONFIGURED = "CONFIGURED"      # settings actually applied
    ENFORCED = "ENFORCED"          # system REFUSES violations, not merely records them
    SUSTAINED = "SUSTAINED"        # continuously in force across an INTERVAL
    VALIDATED = "VALIDATED"        # an adversarial attempt was made and FAILED

    @property
    def rank(self) -> int:
        return _ORDER.index(self)

    def __lt__(self, other: "Lifecycle") -> bool:  # type: ignore[override]
        return self.rank < other.rank


_ORDER = [Lifecycle.UNKNOWN, Lifecycle.SPECIFIED, Lifecycle.CONFIGURED,
          Lifecycle.ENFORCED, Lifecycle.SUSTAINED, Lifecycle.VALIDATED]

# States that CANNOT be established by a single observation. A snapshot certifies state;
# only a history certifies behaviour.
INTERVAL_STATES = frozenset({Lifecycle.SUSTAINED, Lifecycle.VALIDATED})


@dataclass(frozen=True)
class Evidence:
    """One piece of evidence, with the obligation it discharges.

    `interval_start`/`interval_end` are what separate a snapshot from a history. A
    sustainment claim backed only by point-in-time evidence is the same category error
    as a collector reporting HEALTHY from a stale heartbeat.
    """
    kind: str                     # "design_artifact" | "config_read" | "refusal_observed"
                                  # | "transition_log" | "adversarial_test"
    detail: str
    observed_at: str
    epistemic: Epistemic = Epistemic.OBSERVED_PRESENT
    interval_start: Optional[str] = None
    interval_end: Optional[str] = None
    adversarial: bool = False     # a real impersonation/violation attempt was made
    attempt_succeeded: Optional[bool] = None   # None = not attempted
    boundary_exercised: Optional[bool] = None  # did the attempt REACH the enforcement point?
    rejection_reason: Optional[str] = None

    @property
    def spans_interval(self) -> bool:
        return bool(self.interval_start and self.interval_end)

    @property
    def validates(self) -> bool:
        """VALIDATED requires all three, not just a failed attempt.

        WHY boundary_exercised EXISTS: an attempt that failed for an unrelated reason —
        no network, malformed input, missing dependency, wrong URL — also reports
        attempt_succeeded=False. Without this field, an ENVIRONMENTAL FAILURE would
        validate the control. That is a false green produced by the validation
        machinery itself, and it is the same defect class as a collector reporting
        HEALTHY because it could not reach the producer.

        An attempt that never reached the enforcement boundary is INCONCLUSIVE,
        not a demonstration.
        """
        return (self.adversarial is True
                and self.boundary_exercised is True
                and self.attempt_succeeded is False)


_DISCHARGES = {
    "design_artifact": Lifecycle.SPECIFIED,
    "config_read": Lifecycle.CONFIGURED,
    "refusal_observed": Lifecycle.ENFORCED,
    "transition_log": Lifecycle.SUSTAINED,
    "adversarial_test": Lifecycle.VALIDATED,
}


@dataclass
class Control:
    """A governance control. `state` is DERIVED — there is deliberately no setter."""
    control_id: str
    description: str
    evidence: list = field(default_factory=list)

    def add(self, e: Evidence) -> "Control":
        self.evidence.append(e)
        return self

    @property
    def state(self) -> Lifecycle:
        """Highest state whose obligation is actually discharged. Never higher."""
        best = Lifecycle.UNKNOWN
        for e in self.evidence:
            if e.epistemic is not Epistemic.OBSERVED_PRESENT:
                continue
            claimed = _DISCHARGES.get(e.kind)
            if claimed is None:
                continue
            # Interval states demand interval evidence. A snapshot cannot buy SUSTAINED.
            if claimed in INTERVAL_STATES and not e.spans_interval:
                continue
            # VALIDATED demands an adversarial attempt that FAILED.
            if claimed is Lifecycle.VALIDATED and not e.validates:
                continue
            if best < claimed:
                best = claimed
        return best

    def why_not(self, target: Lifecycle) -> Optional[str]:
        """Explain the shortfall. A gate that cannot say why it refused is not a gate."""
        if not (self.state < target):
            return None
        need = {v: k for k, v in _DISCHARGES.items()}[target]
        msg = (f"{self.control_id}: at {self.state.value}, cannot report {target.value}. "
               f"Requires evidence of kind '{need}'")
        if target in INTERVAL_STATES:
            msg += " spanning an interval (interval_start + interval_end)"
        if target is Lifecycle.VALIDATED:
            msg += (", from an adversarial attempt that REACHED the enforcement boundary "
                    "(boundary_exercised=True) and FAILED there (attempt_succeeded=False). "
                    "An attempt blocked by network, malformed input, or an unrelated fault "
                    "is INCONCLUSIVE, not validation.")
        return msg + "."

    def assert_at_most(self, claimed: Lifecycle) -> None:
        """Fail closed when a report would exceed the evidence. NO-FAKE-GREEN for controls."""
        if claimed.rank > self.state.rank:
            raise LifecycleOverclaim(self.why_not(claimed) or "overclaim")


class LifecycleOverclaim(AssertionError):
    """Raised when a control is reported at a state the evidence does not support."""


def resolve(observations: Sequence[Epistemic]) -> Epistemic:
    """Combine observations. UNOBSERVED dominates — unknown propagates.

    An empty sequence is UNOBSERVED, never OBSERVED_ABSENT. 'We found nothing' and
    'we did not look' are different claims; conflating them is how a governance record
    reports a negative finding for a property never examined.
    """
    obs = list(observations)
    if not obs or any(o is Epistemic.UNOBSERVED for o in obs):
        return Epistemic.UNOBSERVED
    if any(o is Epistemic.OBSERVED_ABSENT for o in obs):
        return Epistemic.OBSERVED_ABSENT
    return Epistemic.OBSERVED_PRESENT


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
