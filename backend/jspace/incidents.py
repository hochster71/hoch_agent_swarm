"""Immutable HJOS incident lifecycle.

Findings must not silently disappear when a later cycle returns CONFIRMED_LIVE.
Incidents are append-only: OPEN → ACKNOWLEDGED → CONTAINED → CLOSED (explicit only).
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INCIDENTS = ROOT / "coordination" / "jspace" / "incidents.jsonl"

OPEN_STATUSES = frozenset({"OPEN", "ACKNOWLEDGED", "CONTAINED"})


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _digest(row: dict) -> str:
    body = {k: v for k, v in row.items() if k != "incident_digest"}
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


class IncidentLog:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path else DEFAULT_INCIDENTS
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def open_incident(
        self,
        *,
        subject: str,
        assessment: str,
        observer: str,
        cycle_id: str,
        detail: str,
        recommended_action: str,
        evidence: List[str],
        observation_id: Optional[str] = None,
    ) -> dict:
        """Append OPEN incident. Never updates prior rows."""
        # Dedup key: if an OPEN incident already exists for same subject+assessment, note recurrence
        open_same = [
            r for r in self.read_all()
            if r.get("subject") == subject
            and r.get("assessment") == assessment
            and r.get("status") in OPEN_STATUSES
        ]
        if open_same:
            row = {
                "schema": "HJOS_INCIDENT_EVENT_v1",
                "event": "RECURRENCE",
                "incident_id": open_same[-1]["incident_id"],
                "subject": subject,
                "assessment": assessment,
                "observer": observer,
                "cycle_id": cycle_id,
                "observation_id": observation_id,
                "detail": detail[:500],
                "recommended_action": recommended_action,
                "evidence": evidence,
                "status": open_same[-1]["status"],
                "observed_at": _now(),
            }
        else:
            iid = f"JINC-{time.strftime('%Y%m%d', time.gmtime())}-{uuid.uuid4().hex[:6].upper()}"
            row = {
                "schema": "HJOS_INCIDENT_EVENT_v1",
                "event": "OPEN",
                "incident_id": iid,
                "subject": subject,
                "assessment": assessment,
                "observer": observer,
                "cycle_id": cycle_id,
                "observation_id": observation_id,
                "detail": detail[:500],
                "recommended_action": recommended_action,
                "evidence": evidence,
                "status": "OPEN",
                "observed_at": _now(),
            }
        row["incident_digest"] = _digest(row)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, sort_keys=True) + "\n")
        return row

    def transition(
        self,
        incident_id: str,
        *,
        new_status: str,
        actor: str,
        note: str = "",
    ) -> dict:
        """Explicit lifecycle transition only (never auto-cleared by green cycle)."""
        allowed = {"ACKNOWLEDGED", "CONTAINED", "CLOSED"}
        if new_status not in allowed:
            raise ValueError(f"invalid transition {new_status}")
        row = {
            "schema": "HJOS_INCIDENT_EVENT_v1",
            "event": "TRANSITION",
            "incident_id": incident_id,
            "status": new_status,
            "actor": actor,
            "note": note,
            "observed_at": _now(),
        }
        row["incident_digest"] = _digest(row)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, sort_keys=True) + "\n")
        return row

    def read_all(self) -> List[dict]:
        if not self.path.exists():
            return []
        rows = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return rows

    def open_incidents(self) -> List[dict]:
        """Latest status per incident_id; return those still open."""
        latest: Dict[str, dict] = {}
        for r in self.read_all():
            iid = r.get("incident_id")
            if iid:
                latest[iid] = r
        return [r for r in latest.values() if r.get("status") in OPEN_STATUSES]
