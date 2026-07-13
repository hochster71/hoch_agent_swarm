"""decision_record.py — versioned founder decisions. Only RATIFIED + in-scope authorizes.

FOUNDER-RATIFIED RULES (mechanical, no interpretation):
  * only RATIFIED and non-expired records authorize action;
  * SUPERSEDED, REVOKED, CONFLICTED, EXPIRED never authorize;
  * scope must match mechanically — no implicit wildcard from a MISSING scope field;
  * the source digest must verify;
  * supersession chains must be acyclic.

This is the substrate feedback-ingestion writes to. Without versioned records, an approval
becomes mutable, ambiguous policy — so this comes first.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "coordination" / "founder" / "decision_corpus_v2.jsonl"
SCHEMA = ROOT / "coordination" / "founder" / "decision_schema.json"


class Status(str, Enum):
    DRAFT = "DRAFT"
    PROPOSED = "PROPOSED"
    RATIFIED = "RATIFIED"
    SUPERSEDED = "SUPERSEDED"
    REVOKED = "REVOKED"
    CONFLICTED = "CONFLICTED"
    EXPIRED = "EXPIRED"


# Only these authorize — everything else is DECISION-*-CONTROL rejection surface.
AUTHORIZING = frozenset({Status.RATIFIED})

REQUIRED_FIELDS = (
    "schema_version", "decision_id", "title", "status", "authority", "scope",
    "decision", "rationale", "source_type", "source_reference", "source_sha256",
    "confidence", "effective_at", "created_at", "created_by",
)
SCOPE_DIMS = ("factory_ids", "product_ids", "mission_ids", "environments", "action_types")


class DecisionError(ValueError):
    pass


def compute_source_sha256(source_text: str) -> str:
    return hashlib.sha256(source_text.encode("utf-8")).hexdigest()


@dataclass
class DecisionRecord:
    raw: dict[str, Any]

    @staticmethod
    def validate_schema(d: dict[str, Any]) -> "DecisionRecord":
        """DECISION-SCHEMA-CONTROL-001: reject a record missing required structure."""
        missing = [f for f in REQUIRED_FIELDS if f not in d]
        if missing:
            raise DecisionError(f"decision record missing fields: {missing}")
        if d["status"] not in {s.value for s in Status}:
            raise DecisionError(f"invalid status: {d['status']}")
        scope = d.get("scope", {})
        # DECISION-SCOPE-CONTROL-001: NO implicit wildcard. Every scope dim must be present
        # and be a non-empty list. A missing dim is an error, not "*".
        for dim in SCOPE_DIMS:
            if dim not in scope:
                raise DecisionError(f"scope missing dimension '{dim}' (no implicit wildcard allowed)")
            if not isinstance(scope[dim], list) or not scope[dim]:
                raise DecisionError(f"scope['{dim}'] must be a non-empty list (use ['*'] for all)")
        return DecisionRecord(d)

    def verify_source(self, source_text: str) -> bool:
        """The record's source_sha256 must match the actual source. A changed source hash
        invalidates the record (negative control: source hash changes -> reject)."""
        return self.raw.get("source_sha256") == compute_source_sha256(source_text)

    def is_expired(self, now: float | None = None) -> bool:
        exp = self.raw.get("expires_at")
        if not exp:
            return False
        try:
            t = time.strptime(exp, "%Y-%m-%dT%H:%M:%SZ")
            return time.mktime(t) <= (now or time.time())
        except (ValueError, TypeError):
            return True  # unparseable expiry -> treat as expired (fail closed)

    def authorizes(self, *, factory: str = "*", product: str = "*", mission: str = "*",
                   environment: str = "*", action_type: str = "*",
                   now: float | None = None) -> tuple[bool, str]:
        """The core gate. Returns (authorizes, reason)."""
        st = self.raw.get("status")
        if st != Status.RATIFIED.value:
            return False, f"status={st} does not authorize (only RATIFIED does)"
        if self.is_expired(now):
            return False, "record is EXPIRED"
        if self.raw.get("superseded_by"):
            return False, f"record superseded by {self.raw['superseded_by']}"

        sc = self.raw["scope"]
        checks = [("factory_ids", factory), ("product_ids", product), ("mission_ids", mission),
                  ("environments", environment), ("action_types", action_type)]
        for dim, val in checks:
            allowed = sc[dim]
            if "*" not in allowed and val not in allowed:
                return False, f"scope mismatch on {dim}: '{val}' not in {allowed}"
        return True, "RATIFIED, in scope, not expired"


def load_corpus() -> list[DecisionRecord]:
    if not CORPUS.exists():
        return []
    out = []
    for line in CORPUS.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                out.append(DecisionRecord.validate_schema(json.loads(line)))
            except (json.JSONDecodeError, DecisionError):
                pass
    return out


def supersession_acyclic(records: list[DecisionRecord]) -> tuple[bool, str]:
    """DECISION-SUPERSESSION-CONTROL: the supersedes graph must be a DAG."""
    ids = {r.raw["decision_id"]: r for r in records}
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {i: WHITE for i in ids}

    def visit(i: str) -> bool:
        color[i] = GRAY
        for nxt in ids[i].raw.get("supersedes", []):
            if nxt not in ids:
                continue
            if color[nxt] == GRAY:
                return False
            if color[nxt] == WHITE and not visit(nxt):
                return False
        color[i] = BLACK
        return True

    for i in ids:
        if color[i] == WHITE and not visit(i):
            return False, f"supersession cycle through {i}"
    return True, "supersession chain is acyclic"


def apply_supersession(records: list[DecisionRecord]) -> list[DecisionRecord]:
    """Mark any record named in another's `supersedes` as SUPERSEDED (cannot authorize)."""
    superseded = {sid for r in records for sid in r.raw.get("supersedes", [])}
    for r in records:
        if r.raw["decision_id"] in superseded and r.raw.get("status") == Status.RATIFIED.value:
            r.raw["status"] = Status.SUPERSEDED.value
    return records
