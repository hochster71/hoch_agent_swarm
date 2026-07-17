"""Mission transactions — proposal → validate → authorize → commit → event → truth.

OS-like write path for Executive Mission. Actors never bypass this for material writes.
"""
from __future__ import annotations

import json
import os
import tempfile
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.helm_runtime.event_bus import publish_event
from backend.helm_runtime.governance_engine import authorize, normalize_role, validate_proposal
from backend.helm_runtime.truth_engine import recompute_projections

ROOT = Path(__file__).resolve().parents[2]
EXEC_PATH = ROOT / "coordination" / "goal" / "executive_mission.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _atomic_write(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2) + "\n"
    fd, tmp = tempfile.mkstemp(prefix=".exec_mission.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _set_path(doc: Dict[str, Any], dotted: str, value: Any) -> None:
    """Set a.b.c on nested dict; creates dict parents."""
    parts = dotted.split(".")
    cur: Any = doc
    for p in parts[:-1]:
        if p not in cur or not isinstance(cur[p], dict):
            cur[p] = {}
        cur = cur[p]
    cur[parts[-1]] = value


class MissionTransaction:
    """BEGIN → … → END envelope for one mission commit."""

    def __init__(
        self,
        role: str,
        patch: Dict[str, Any],
        *,
        correlation_id: Optional[str] = None,
        actor: Optional[str] = None,
        evidence: Optional[List[str]] = None,
        note: str = "",
        founder_token_present: bool = False,
        path: Path = EXEC_PATH,
        recompute_truth: bool = True,
        expected_parent_version: Optional[int] = None,
    ):
        self.role = normalize_role(role)
        self.patch = dict(patch)
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.actor = actor or self.role
        self.evidence = list(evidence or [])
        self.note = note
        self.founder_token_present = founder_token_present
        self.path = path
        self.recompute_truth = recompute_truth
        # Optimistic concurrency: if set, commit is refused unless the on-disk
        # mission_version still equals this value (compare-and-swap). Prevents
        # concurrent workers from silently clobbering each other's writes.
        self.expected_parent_version = expected_parent_version
        self.transaction_id = str(uuid.uuid4())
        self.status = "BEGIN"

    def run(self) -> Dict[str, Any]:
        self.status = "PROPOSAL"
        if not self.path.exists():
            self.status = "FAILED"
            return {"ok": False, "status": self.status, "error": f"missing {self.path}"}

        doc = json.loads(self.path.read_text(encoding="utf-8"))
        parent_version = int(doc.get("mission_version") or 0)

        # Optimistic-concurrency guard (compare-and-swap). Refuse stale writes.
        if (
            self.expected_parent_version is not None
            and int(self.expected_parent_version) != parent_version
        ):
            self.status = "CONFLICT"
            return {
                "ok": False,
                "status": self.status,
                "phase": "OPTIMISTIC_CONCURRENCY",
                "error": "stale mission_version",
                "expected_parent_version": int(self.expected_parent_version),
                "actual_parent_version": parent_version,
            }

        self.status = "VALIDATE"
        ok, errs = validate_proposal(self.role, self.patch)
        if not ok:
            self.status = "FAILED"
            return {"ok": False, "status": self.status, "phase": "VALIDATE", "errors": errs}

        self.status = "AUTHORIZE"
        ok, reason = authorize(
            self.role, self.patch, founder_token_present=self.founder_token_present
        )
        if not ok:
            self.status = "FAILED"
            return {"ok": False, "status": self.status, "phase": "AUTHORIZE", "error": reason}

        self.status = "COMMIT"
        new_doc = deepcopy(doc)
        for k, v in self.patch.items():
            # Map mission.* into nested structures when present
            if k.startswith("mission.") and "mission" in new_doc:
                _set_path(new_doc, k, v)
            elif k.startswith("orchestration.") or k.startswith("engineering.") or k.startswith("assurance."):
                _set_path(new_doc, k, v)
            elif k.startswith("mission.") and "mission" not in new_doc:
                _set_path(new_doc, k, v)
            else:
                # top-level owned blobs
                if k in ("orchestration", "engineering", "assurance") and isinstance(v, dict):
                    new_doc[k] = {**(new_doc.get(k) or {}), **v}
                else:
                    _set_path(new_doc, k, v)

        new_version = parent_version + 1
        new_doc["mission_version"] = new_version
        new_doc["transaction_id"] = self.transaction_id
        new_doc["parent_version"] = parent_version
        new_doc["updated_at"] = _now()
        if not new_doc.get("created_at"):
            new_doc["created_at"] = new_doc["updated_at"]
        new_doc["correlation_id"] = self.correlation_id

        writes = list(new_doc.get("last_writes") or [])
        writes.append(
            {
                "at_utc": new_doc["updated_at"],
                "role": self.role,
                "actor": self.actor,
                "fields": list(self.patch.keys()),
                "artifact": str(self.path.relative_to(ROOT)) if self.path.is_relative_to(ROOT) else str(self.path),
                "correlation_id": self.correlation_id,
                "transaction_id": self.transaction_id,
                "mission_version": new_version,
                "parent_version": parent_version,
                "note": self.note,
            }
        )
        new_doc["last_writes"] = writes[-50:]
        _atomic_write(self.path, new_doc)

        self.status = "PUBLISH_EVENT"
        mission_id = (new_doc.get("mission") or {}).get("id") or "UNKNOWN"
        # Resolve event bus path at call time so tests can monkeypatch EVENTS_PATH
        from backend.helm_runtime import event_bus as _eb

        ev = publish_event(
            type="MISSION_TRANSACTION_COMMITTED",
            producer=self.actor,
            mission_id=mission_id,
            correlation_id=self.correlation_id,
            evidence=self.evidence,
            payload={
                "role": self.role,
                "fields": list(self.patch.keys()),
                "note": self.note,
            },
            mission_version=new_version,
            transaction_id=self.transaction_id,
            path=_eb.EVENTS_PATH,
        )

        truth: Dict[str, Any] = {}
        if self.recompute_truth:
            self.status = "RECOMPUTE_TRUTH"
            truth = recompute_projections(mission_id=mission_id)

        self.status = "END"
        return {
            "ok": True,
            "status": self.status,
            "transaction_id": self.transaction_id,
            "mission_version": new_version,
            "parent_version": parent_version,
            "correlation_id": self.correlation_id,
            "event_id": ev.event_id,
            "truth_projection_summary": {
                "errors": truth.get("errors"),
                "mission_overall": (truth.get("projections") or {}).get("mission_state", {}).get("overall"),
            },
        }


def commit_proposal(
    role: str,
    patch: Dict[str, Any],
    **kwargs: Any,
) -> Dict[str, Any]:
    return MissionTransaction(role, patch, **kwargs).run()
