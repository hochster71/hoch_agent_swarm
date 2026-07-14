"""Append-only J-SPACE truth ledgers.

HJOS may create evidence and alerts. It must never rewrite HELM authoritative state
(task DB rows, leases, founder decisions, soak seals).
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from backend.jspace.schema import (
    JSpaceAlert,
    JSpaceAssessment,
    JSpaceEvent,
    JSpaceHealth,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_JSPACE_DIR = ROOT / "coordination" / "jspace"


class JSpaceLedger:
    """Append-only store under coordination/jspace/ (or a test override)."""

    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = Path(root) if root else DEFAULT_JSPACE_DIR
        self.root.mkdir(parents=True, exist_ok=True)
        self.events_path = self.root / "events.jsonl"
        self.assessments_path = self.root / "assessments.jsonl"
        self.alerts_path = self.root / "alerts.jsonl"
        self.health_path = self.root / "health.json"
        self.cycles_path = self.root / "cycles.jsonl"
        self.quarantine_requests_path = self.root / "quarantine_requests.jsonl"

    def append_event(self, event: JSpaceEvent) -> dict:
        return self._append(self.events_path, event.to_dict())

    def append_assessment(self, assessment: JSpaceAssessment) -> dict:
        d = assessment.to_dict()
        if d.get("state_mutated"):
            raise PermissionError("ledger refuses state_mutated assessment")
        return self._append(self.assessments_path, d)

    def append_alert(self, alert: JSpaceAlert) -> dict:
        return self._append(self.alerts_path, alert.to_dict())

    def write_health(self, health: JSpaceHealth) -> dict:
        d = health.to_dict()
        self._atomic_write_json(self.health_path, d)
        self._append(self.cycles_path, {
            "cycle_id": d["cycle_id"],
            "overall": d["overall"],
            "observed_at": d["observed_at"],
            "open_alerts": d["open_alerts"],
            "recommended_action": d["recommended_action"],
            "health_digest": d["health_digest"],
        })
        return d

    def request_quarantine(self, request: Dict[str, Any]) -> dict:
        """Record a quarantine REQUEST only. Does not execute quarantine."""
        payload = {
            **request,
            "executed": False,
            "execution_authority": "NONE",
            "note": "HJOS may request quarantine; automatic quarantine disabled until burn-in",
        }
        return self._append(self.quarantine_requests_path, payload)

    def read_jsonl(self, path: Path, *, limit: Optional[int] = None) -> List[dict]:
        if not path.exists():
            return []
        rows: List[dict] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        if limit is not None and limit >= 0:
            return rows[-limit:]
        return rows

    def recent_assessments(self, *, limit: int = 200) -> List[dict]:
        return self.read_jsonl(self.assessments_path, limit=limit)

    def recent_alerts(self, *, limit: int = 100) -> List[dict]:
        return self.read_jsonl(self.alerts_path, limit=limit)

    def latest_health(self) -> Optional[dict]:
        if not self.health_path.exists():
            return None
        try:
            return json.loads(self.health_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    @staticmethod
    def _append(path: Path, row: dict) -> dict:
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(row, sort_keys=True, default=str) + "\n"
        with path.open("a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
        return row

    @staticmethod
    def _atomic_write_json(path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, sort_keys=True, default=str)
                f.write("\n")
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
