"""Event Bus — Digital Nervous System.

Nothing material should communicate only via chat. Publish events here.
Append-only JSONL under coordination/events/helm_events.jsonl.
"""
from __future__ import annotations

import json
import os
import tempfile
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
EVENTS_PATH = ROOT / "coordination" / "events" / "helm_events.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Event:
    event_id: str
    correlation_id: str
    mission_id: str
    producer: str
    type: str
    timestamp: str
    evidence: List[str] = field(default_factory=list)
    payload: Dict[str, Any] = field(default_factory=dict)
    mission_version: Optional[int] = None
    transaction_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def publish_event(
    *,
    type: str,
    producer: str,
    mission_id: str,
    correlation_id: Optional[str] = None,
    evidence: Optional[List[str]] = None,
    payload: Optional[Dict[str, Any]] = None,
    mission_version: Optional[int] = None,
    transaction_id: Optional[str] = None,
    path: Optional[Path] = None,
) -> Event:
    """Append one event. Fail-closed on I/O errors (caller handles)."""
    path = path or EVENTS_PATH
    ev = Event(
        event_id=str(uuid.uuid4()),
        correlation_id=correlation_id or str(uuid.uuid4()),
        mission_id=mission_id,
        producer=producer,
        type=type,
        timestamp=_now(),
        evidence=list(evidence or []),
        payload=dict(payload or {}),
        mission_version=mission_version,
        transaction_id=transaction_id,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(ev.to_dict(), sort_keys=True) + "\n"
    # Append with fsync for durability (AU-ish)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(line)
        fh.flush()
        os.fsync(fh.fileno())
    return ev


def tail_events(n: int = 20, path: Path = EVENTS_PATH) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    out = []
    for ln in lines[-n:]:
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            out.append({"type": "MALFORMED_EVENT", "raw": ln[:200]})
    return out
