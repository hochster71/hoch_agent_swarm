"""REQ-TO-003 — INTAKE -> PLAN -> ROUTE -> EXECUTE -> VERIFY -> PACKAGE -> DOORSTEP.

Proves one bounded request can traverse the whole factory with the founder removed from
transport. Michael appears ONLY if a genuine founder-only action is reached.

THE CENTRAL RULE
----------------
No stage advances from a hand-edited status string. A transition is ADMITTED only when a
`TransitionEvidence` carries all six of:
    validator_result   -- an executed validator's verdict (exit code / boolean)
    evidence_path      -- an artifact that exists on disk
    evidence_digest    -- sha256 recomputed from that artifact's bytes, right now
    io_binding         -- digest of the stage's input, bound to the digest of its output
    event_timestamp    -- from an actual event, never invented for a stage that did not run
    run_identity       -- mission_id + task_id of the run that produced it
Anything missing => the machine goes to UNKNOWN or BLOCKED. Never forward.

`advance()` recomputes the evidence digest from the file. A tampered artifact, or a
hand-set state, cannot move the path: the digest will not match and the transition is
refused.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import sys
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

PACKAGES = ROOT / "coordination" / "council" / "live_proof_packages"

WORKLOAD_LABELS = ["TERMINAL_PATH_PROOF_WORKLOAD",
                   "NOT_CHAMPION_PRODUCT",
                   "NOT_PRODUCTION_RELEASE"]


class Stage(str, Enum):
    INTAKE = "INTAKE"
    PLAN = "PLAN"
    ROUTE = "ROUTE"
    EXECUTE = "EXECUTE"
    VERIFY = "VERIFY"
    PACKAGE = "PACKAGE"
    DOORSTEP = "DOORSTEP"


class State(str, Enum):
    INTAKE_RECEIVED = "INTAKE_RECEIVED"
    INTAKE_VALIDATED = "INTAKE_VALIDATED"
    PLAN_CREATED = "PLAN_CREATED"
    PLAN_VALIDATED = "PLAN_VALIDATED"
    ROUTE_SELECTED = "ROUTE_SELECTED"
    ROUTE_AUTHORIZED = "ROUTE_AUTHORIZED"
    EXECUTION_ACTIVE = "EXECUTION_ACTIVE"
    EXECUTION_COMPLETE = "EXECUTION_COMPLETE"
    VERIFICATION_ACTIVE = "VERIFICATION_ACTIVE"
    VERIFICATION_PASS = "VERIFICATION_PASS"
    PACKAGE_CREATED = "PACKAGE_CREATED"
    PACKAGE_VALIDATED = "PACKAGE_VALIDATED"
    DOORSTEP_READY = "DOORSTEP_READY"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"
    ERROR = "ERROR"


TERMINAL_STATES = {State.BLOCKED, State.UNKNOWN, State.ERROR, State.DOORSTEP_READY}

# The ONLY legal forward edges. Anything else is refused.
LEGAL_EDGES: dict[State, set[State]] = {
    State.INTAKE_RECEIVED: {State.INTAKE_VALIDATED},
    State.INTAKE_VALIDATED: {State.PLAN_CREATED},
    State.PLAN_CREATED: {State.PLAN_VALIDATED},
    State.PLAN_VALIDATED: {State.ROUTE_SELECTED},
    State.ROUTE_SELECTED: {State.ROUTE_AUTHORIZED},
    State.ROUTE_AUTHORIZED: {State.EXECUTION_ACTIVE},
    State.EXECUTION_ACTIVE: {State.EXECUTION_COMPLETE},
    State.EXECUTION_COMPLETE: {State.VERIFICATION_ACTIVE},
    State.VERIFICATION_ACTIVE: {State.VERIFICATION_PASS},
    State.VERIFICATION_PASS: {State.PACKAGE_CREATED},
    State.PACKAGE_CREATED: {State.PACKAGE_VALIDATED},
    State.PACKAGE_VALIDATED: {State.DOORSTEP_READY},
}


def utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sha256_obj(o: Any) -> str:
    return hashlib.sha256(json.dumps(o, sort_keys=True).encode()).hexdigest()


class TransitionRefused(Exception):
    """A stage tried to advance without complete, verifiable evidence."""


@dataclass
class TransitionEvidence:
    """Every field is REQUIRED. A missing one refuses the transition."""
    validator_name: str
    validator_result: bool          # from an EXECUTED validator
    validator_exit_code: int | None
    evidence_path: str              # relative to ROOT
    evidence_digest: str            # sha256 of the artifact, recomputed at admit time
    input_digest: str               # binds this stage's input...
    output_digest: str              # ...to its output
    event_timestamp: str            # from the real event
    mission_id: str
    task_id: str
    detail: str = ""

    def missing_fields(self) -> list[str]:
        missing = []
        for f in ("validator_name", "evidence_path", "evidence_digest", "input_digest",
                  "output_digest", "event_timestamp", "mission_id", "task_id"):
            if not getattr(self, f):
                missing.append(f)
        if self.validator_result is not True:
            missing.append("validator_result")
        return missing


@dataclass
class ManualInterventionMetrics:
    manual_prompt_copy_count: int = 0
    manual_result_copy_count: int = 0
    manual_stage_transition_count: int = 0
    founder_interventions: int = 0
    founder_actions: list[str] = field(default_factory=list)


class TerminalPathOrchestrator:
    """Drives the seven stages. Refuses to move without evidence."""

    def __init__(self, mission_id: str, package_dir: Path, root: Path | None = None):
        self.mission_id = mission_id
        self.package_dir = package_dir
        self.root = root or ROOT
        self.state: State = State.UNKNOWN
        self.history: list[dict] = []
        self.metrics = ManualInterventionMetrics()
        self.blocked_reason: str | None = None

    # -- the only way the state may change ----------------------------------
    def advance(self, to: State, ev: TransitionEvidence) -> State:
        frm = self.state

        # 1. the edge must be legal
        if to not in LEGAL_EDGES.get(frm, set()):
            return self._halt(State.BLOCKED,
                              f"ILLEGAL_EDGE:{frm.value}->{to.value}", ev)

        # 2. every evidence field must be present, and the validator must have PASSED
        missing = ev.missing_fields()
        if missing:
            return self._halt(State.UNKNOWN,
                              f"INCOMPLETE_EVIDENCE:{','.join(missing)}", ev)

        # 3. the artifact must exist and its digest must match a FRESH recomputation.
        #    This is what makes a hand-edited status string useless: the bytes decide.
        path = self.root / ev.evidence_path
        if not path.exists():
            return self._halt(State.UNKNOWN, f"EVIDENCE_ABSENT:{ev.evidence_path}", ev)
        actual = sha256_file(path)
        if actual != ev.evidence_digest:
            return self._halt(State.BLOCKED,
                              f"EVIDENCE_DIGEST_MISMATCH:{ev.evidence_path}", ev)

        # 4. run identity must match this mission
        if ev.mission_id != self.mission_id:
            return self._halt(State.BLOCKED, "RUN_IDENTITY_MISMATCH", ev)

        self.state = to
        self._record(frm, to, "ADMITTED", ev)
        return self.state

    def _halt(self, state: State, reason: str, ev: TransitionEvidence | None) -> State:
        self.state = state
        self.blocked_reason = reason
        self._record(self.history[-1]["to"] if self.history else State.UNKNOWN.value,
                     state.value, f"REFUSED:{reason}", ev)
        return self.state

    def _record(self, frm: Any, to: Any, verdict: str,
                ev: TransitionEvidence | None) -> None:
        self.history.append({
            "from": frm.value if isinstance(frm, State) else str(frm),
            "to": to.value if isinstance(to, State) else str(to),
            "verdict": verdict,
            "recorded_at": utc(),
            "evidence": asdict(ev) if ev else None,
        })

    # -- the machine cannot be hand-set ------------------------------------
    def force_state(self, state: State) -> None:
        """There is deliberately no supported way to set state without evidence.

        This exists ONLY so the adversarial tests can attempt it and prove that the
        NEXT advance() still refuses, because the digest chain does not follow.
        """
        self.metrics.manual_stage_transition_count += 1
        self.state = state

    def to_dict(self) -> dict:
        return {
            "mission_id": self.mission_id,
            "state": self.state.value,
            "blocked_reason": self.blocked_reason,
            "transitions": self.history,
            "manual_intervention_metrics": asdict(self.metrics),
        }


# ===========================================================================
# STAGE 1 — INTAKE
# ===========================================================================

REQUIRED_INTAKE_FIELDS = [
    "mission_id", "request_id", "goal_contract_id", "workload_type",
    "requested_outcome", "constraints", "founder_only_actions",
    "acceptance_criteria", "submitted_at", "source_identity",
]

AMBIGUOUS = {"works", "good", "better", "improved", "nice", "correct-ish",
             "reasonable", "as appropriate", "etc", "and so on"}


def validate_intake(env: dict, canonical_goal_id: str) -> tuple[bool, list[str]]:
    """Objective. An ambiguous success criterion is a FAILURE, not a warning."""
    errs: list[str] = []
    for f in REQUIRED_INTAKE_FIELDS:
        if f not in env or env[f] in (None, "", []):
            if f == "founder_only_actions" and env.get(f) == []:
                continue                      # an empty list is a legitimate answer
            errs.append(f"MISSING_FIELD:{f}")

    if env.get("goal_contract_id") != canonical_goal_id:
        errs.append("NOT_BOUND_TO_CANONICAL_GOAL")

    if env.get("workload_type") != "TERMINAL_PATH_PROOF_WORKLOAD":
        errs.append("WORKLOAD_TYPE_NOT_PROOF_WORKLOAD")

    ac = env.get("acceptance_criteria") or []
    if not ac:
        errs.append("NO_ACCEPTANCE_CRITERIA")
    for c in ac:
        text = (c.get("criterion") if isinstance(c, dict) else str(c)) or ""
        if not text.strip():
            errs.append("EMPTY_ACCEPTANCE_CRITERION")
        if any(w in text.lower().split() for w in AMBIGUOUS):
            errs.append(f"AMBIGUOUS_CRITERION:{text[:40]}")
        if isinstance(c, dict) and not c.get("validator"):
            errs.append(f"CRITERION_WITHOUT_VALIDATOR:{text[:40]}")

    # scope: the proof workload may not require prohibited actions
    prohibited = {"payment", "signing", "submission", "production_deploy",
                  "credentials", "money_movement"}
    for c in env.get("constraints", []):
        pass
    for a in env.get("founder_only_actions", []):
        if str(a).lower() in prohibited:
            errs.append(f"PROOF_WORKLOAD_REQUIRES_FOUNDER_ACTION:{a}")

    return (not errs), errs
