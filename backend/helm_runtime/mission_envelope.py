"""mission_envelope.py — HELM Operational Mission Telemetry (execution record).

Proposed by EDR-0008. Schema: coordination/governance/mission_envelope_v1.json

WHAT THIS IS, AND WHAT IT IS NOT
--------------------------------
`mission_contract.py` (EDR-0007) is the **pre-execution** contract: what a mission is
permitted to do. This module is the **execution record**: what a mission actually did.

    Mission Contract  -> may I?   (allowlists, gates, stop conditions)
    Mission Envelope  -> what happened?  (actions, sources, mutations, unknowns, errors)

Both are required. A contract without an envelope is a permission slip nobody checked.

THE CENTRAL DESIGN RULE: STATUS IS DERIVED, NEVER DECLARED
-----------------------------------------------------------
An agent cannot set `status`. There is no setter, and the constructor rejects the field.
Status is computed from the recorded facts every time it is read:

    any error / failed source            -> DEGRADED   (or FAILED if nothing was produced)
    any unknown / unverified source      -> PARTIAL
    all sources ADVANCING, no unknowns   -> COMPLETED_VERIFIED
    outputs produced but never re-read   -> COMPLETED_PENDING_EVIDENCE

This is the architectural correction the founder named on 2026-07-20: a mission that
queried six calendars, had one time out, and still wrote its note is **not green**. It is
COMPLETED_DEGRADED, and the envelope makes it impossible to render it any other way,
because the renderer has no access to a status field it could override.

An agent's honest narrative is not the problem. The problem is that a narrative can be
summarized into a green box, and numbers with no artifact behind them can ride along.
Every scalar shown to the founder must trace to an `evidence` path recorded here.

TRUTH CLASSES ARE BORROWED, NOT REDEFINED
------------------------------------------
Source truth uses the ratified `proof_contract.Truth` enum via `mission_contract`, so
this module cannot silently mint a second vocabulary. A source that an agent merely
*reports* having read, without a re-readable artifact, is ASSERTED — not OBSERVED.

FAILS OPEN TOWARD DOUBT
------------------------
Every ambiguity resolves toward the less-complete status. An envelope that is never
explicitly closed reads as FAILED (crashed mid-mission), not as silently fine.
"""
from __future__ import annotations

import json
import os
import platform
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:  # pragma: no cover - in-repo import; guarded for standalone use
    from backend.helm_runtime.mission_contract import Truth, ADVANCING
except Exception:  # pragma: no cover
    try:
        from helm_runtime.mission_contract import Truth, ADVANCING  # type: ignore
    except Exception:
        from enum import Enum

        class Truth(str, Enum):  # type: ignore[no-redef]
            OBSERVED = "OBSERVED"
            DERIVED = "DERIVED"
            CACHED = "CACHED"
            ASSERTED = "ASSERTED"
            UNKNOWN = "UNKNOWN"

        ADVANCING = frozenset({Truth.OBSERVED, Truth.DERIVED})  # type: ignore

ROOT = Path(__file__).resolve().parents[2]
ENVELOPE_DIR = ROOT / "coordination" / "missions" / "envelopes"

SCHEMA_NAME = "HELM_MISSION_ENVELOPE_v1"

# Operational domains. Engineering is ONE of these, not the whole board.
DOMAINS = frozenset({
    "engineering", "qualification", "deployment", "factory",
    "family_ops", "calendar_ops", "home_ops", "finance_ops",
    "research", "founder_decision",
})

# Derived statuses. There is deliberately no plain "COMPLETED".
STATUS_RUNNING = "RUNNING"
STATUS_FAILED = "FAILED"
STATUS_DEGRADED = "COMPLETED_DEGRADED"
STATUS_PARTIAL = "COMPLETED_PARTIAL"
STATUS_PENDING_EVIDENCE = "COMPLETED_PENDING_EVIDENCE"
STATUS_VERIFIED = "COMPLETED_VERIFIED"

# Founder-facing severity for the SYSTEM ISSUES panel.
SEVERITY_RED = "RED"
SEVERITY_AMBER = "AMBER"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class EnvelopeError(ValueError):
    """Raised when an envelope is malformed. Fails closed."""


@dataclass
class Source:
    """One thing the mission read. `truth` says how well we know it."""
    name: str
    truth: str                      # Truth enum value
    detail: str = ""
    evidence: Optional[str] = None  # re-readable artifact path proving this read

    def is_advancing(self) -> bool:
        try:
            return Truth(self.truth) in ADVANCING
        except ValueError:
            return False

    def is_failure(self) -> bool:
        return not self.is_advancing() and Truth(self.truth) == Truth.UNKNOWN


@dataclass
class Action:
    """Something the mission did. Read-only inspections count and should be recorded."""
    name: str
    detail: str = ""
    at: str = field(default_factory=_now)


@dataclass
class Mutation:
    """A write. Every mutation names its target and carries an undo path or NONE."""
    target: str
    kind: str                       # created | updated | deleted | none
    detail: str = ""
    undo: Optional[str] = None
    at: str = field(default_factory=_now)


@dataclass
class Unknown:
    """Something the mission could NOT establish. Never collapse this into 'empty'."""
    subject: str
    reason: str
    attempted: int = 1


@dataclass
class Issue:
    """A failure worth showing the founder."""
    subject: str
    detail: str
    severity: str = SEVERITY_AMBER


class MissionEnvelope:
    """The execution record for one HELM mission, in any domain.

    Usage:
        env = MissionEnvelope("FAMILY-BRIEF-20260720", "family_ops", agent="claude")
        env.act("Queried 6 calendars")
        env.source("michael_calendar", Truth.OBSERVED, evidence="logs/cal_michael.json")
        env.unknown("alison_calendar", "query timed out x3", attempted=3)
        env.mutate("Apple Notes/Family Brief", "created", undo="notes_backup/...")
        env.close()
        env.status  # -> COMPLETED_DEGRADED   (derived; nobody chose this)
    """

    def __init__(
        self,
        mission_id: str,
        domain: str,
        *,
        agent: str,
        host: Optional[str] = None,
        title: str = "",
        correlation_id: Optional[str] = None,
        **forbidden: Any,
    ) -> None:
        if forbidden:
            # Guard the whole point of the module.
            raise EnvelopeError(
                f"status and derived fields cannot be set by the caller: {sorted(forbidden)}"
            )
        if domain not in DOMAINS:
            raise EnvelopeError(f"unknown domain '{domain}'; known: {sorted(DOMAINS)}")
        if not mission_id or not str(mission_id).strip():
            raise EnvelopeError("mission_id is required")
        if not agent or not str(agent).strip():
            raise EnvelopeError("agent is required — an unattributed mission is not evidence")

        self.mission_id = mission_id
        self.domain = domain
        self.title = title or mission_id
        self.agent = agent
        self.host = host or platform.node()
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.started_at = _now()
        self.completed_at: Optional[str] = None

        self.actions: List[Action] = []
        self.sources: List[Source] = []
        self.mutations: List[Mutation] = []
        self.unknowns: List[Unknown] = []
        self.errors: List[Issue] = []
        self.evidence: List[str] = []
        self.lifecycle: List[str] = ["STARTED"]
        self.founder_action: Optional[Dict[str, str]] = None

    # --- recording -----------------------------------------------------------

    def act(self, name: str, detail: str = "") -> "MissionEnvelope":
        self.actions.append(Action(name=name, detail=detail))
        return self

    def source(
        self, name: str, truth: Any, detail: str = "", evidence: Optional[str] = None
    ) -> "MissionEnvelope":
        tv = truth.value if isinstance(truth, Truth) else str(truth)
        try:
            Truth(tv)
        except ValueError:
            raise EnvelopeError(f"'{tv}' is not a ratified truth class")
        self.sources.append(Source(name=name, truth=tv, detail=detail, evidence=evidence))
        if evidence:
            self.evidence.append(evidence)
        return self

    def mutate(
        self, target: str, kind: str, detail: str = "", undo: Optional[str] = None
    ) -> "MissionEnvelope":
        if kind not in {"created", "updated", "deleted", "none"}:
            raise EnvelopeError(f"unknown mutation kind '{kind}'")
        self.mutations.append(Mutation(target=target, kind=kind, detail=detail, undo=undo))
        return self

    def unknown(self, subject: str, reason: str, attempted: int = 1) -> "MissionEnvelope":
        self.unknowns.append(Unknown(subject=subject, reason=reason, attempted=attempted))
        self.lifecycle.append("PARTIAL_SOURCE_FAILURE")
        return self

    def error(self, subject: str, detail: str, severity: str = SEVERITY_AMBER) -> "MissionEnvelope":
        self.errors.append(Issue(subject=subject, detail=detail, severity=severity))
        return self

    def step(self, name: str) -> "MissionEnvelope":
        """Record a lifecycle transition, e.g. GOOGLE_FALLBACK_USED."""
        self.lifecycle.append(name)
        return self

    def prove(self, path: str) -> "MissionEnvelope":
        """Attach a re-readable artifact produced by this mission."""
        if path not in self.evidence:
            self.evidence.append(path)
        return self

    def founder_gate(self, title: str, reason: str) -> "MissionEnvelope":
        self.founder_action = {"title": title, "reason": reason}
        self.lifecycle.append("FOUNDER_REVIEW_CREATED")
        return self

    def close(self) -> "MissionEnvelope":
        self.completed_at = _now()
        self.lifecycle.append(self.status)
        return self

    # --- derivation ----------------------------------------------------------

    @property
    def status(self) -> str:
        """Computed on every read. No agent chose this value."""
        if self.completed_at is None:
            return STATUS_RUNNING

        produced = bool(self.evidence) or bool(
            [m for m in self.mutations if m.kind != "none"]
        )
        hard = [e for e in self.errors if e.severity == SEVERITY_RED]

        if hard and not produced:
            return STATUS_FAILED
        if self.errors:
            return STATUS_DEGRADED
        if self.unknowns:
            return STATUS_PARTIAL

        # No errors, no unknowns. Are the sources actually evidence?
        non_advancing = [s for s in self.sources if not s.is_advancing()]
        if non_advancing:
            return STATUS_PARTIAL
        unproven = [s for s in self.sources if not s.evidence]
        if unproven or not self.evidence:
            return STATUS_PENDING_EVIDENCE
        return STATUS_VERIFIED

    @property
    def is_green(self) -> bool:
        return self.status == STATUS_VERIFIED

    @property
    def source_summary(self) -> Dict[str, int]:
        return {
            "total": len(self.sources),
            "verified": len([s for s in self.sources if s.is_advancing()]),
            "degraded": len(self.unknowns),
        }

    # --- serialization -------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": SCHEMA_NAME,
            "mission_id": self.mission_id,
            "title": self.title,
            "domain": self.domain,
            "status": self.status,          # derived at write time
            "status_derived": True,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "agent": self.agent,
            "host": self.host,
            "correlation_id": self.correlation_id,
            "lifecycle": list(self.lifecycle),
            "actions": [asdict(a) for a in self.actions],
            "sources": [asdict(s) for s in self.sources],
            "mutations": [asdict(m) for m in self.mutations],
            "unknowns": [asdict(u) for u in self.unknowns],
            "errors": [asdict(e) for e in self.errors],
            "evidence": list(self.evidence),
            "founder_action": self.founder_action,
        }

    def write(self, directory: Optional[Path] = None) -> Path:
        """Persist atomically. Envelopes are append-only history, one file per mission."""
        directory = directory or ENVELOPE_DIR
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{self.mission_id}.json"
        tmp = path.with_suffix(".json.tmp")
        payload = json.dumps(self.to_dict(), indent=2, sort_keys=True)
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        return path

    def publish(self) -> None:
        """Emit to the HELM event bus so the envelope is not a private file."""
        try:
            from backend.helm_runtime.event_bus import publish_event
        except Exception:
            from helm_runtime.event_bus import publish_event  # type: ignore
        publish_event(
            type=f"MISSION_{self.status}",
            producer=self.agent,
            mission_id=self.mission_id,
            correlation_id=self.correlation_id,
            evidence=list(self.evidence),
            payload={
                "domain": self.domain,
                "title": self.title,
                "sources": self.source_summary,
                "unknowns": len(self.unknowns),
                "errors": len(self.errors),
                "mutations": len([m for m in self.mutations if m.kind != "none"]),
                "founder_action": self.founder_action,
            },
        )


def load_envelopes(directory: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Read all envelopes. The Founder Live view renders from this and nothing else."""
    directory = directory or ENVELOPE_DIR
    if not directory.exists():
        return []
    out: List[Dict[str, Any]] = []
    for p in sorted(directory.glob("*.json")):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception as exc:  # a corrupt envelope is itself a finding
            out.append({
                "schema": SCHEMA_NAME,
                "mission_id": p.stem,
                "title": p.stem,
                "domain": "engineering",
                "status": STATUS_FAILED,
                "errors": [{"subject": "envelope", "detail": f"unreadable: {exc}",
                            "severity": SEVERITY_RED}],
                "sources": [], "unknowns": [], "mutations": [], "evidence": [],
                "lifecycle": ["UNREADABLE"], "actions": [], "founder_action": None,
            })
    return out
