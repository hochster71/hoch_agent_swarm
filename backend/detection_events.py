from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any
import json
from pathlib import Path
from uuid import uuid4

@dataclass
class DetectionEvent:
    event_id: str
    timestamp: str
    event_family: str
    severity: str
    source_log: str
    actor: str | None
    caller_node: str | None
    caller_tier: str | None
    skill_id: str | None
    prompt_id: str | None
    task_id: str | None
    approval_id: str | None
    provider: str | None
    model: str | None
    verdict: str | None
    reason: str | None
    risk_level: str | None
    metadata: dict[str, Any]

class DetectionEventBus:
    def __init__(self, path: str = "audit/detection_events.jsonl") -> None:
        # Resolve path relative to repository base
        base = Path(__file__).parent.parent
        self.path = base / path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(
        self,
        *,
        event_family: str,
        severity: str,
        source_log: str,
        actor: str | None = None,
        caller_node: str | None = None,
        caller_tier: str | None = None,
        skill_id: str | None = None,
        prompt_id: str | None = None,
        task_id: str | None = None,
        approval_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        verdict: str | None = None,
        reason: str | None = None,
        risk_level: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DetectionEvent:
        event = DetectionEvent(
            event_id=f"det-{uuid4()}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_family=event_family,
            severity=severity,
            source_log=source_log,
            actor=actor,
            caller_node=caller_node,
            caller_tier=caller_tier,
            skill_id=skill_id,
            prompt_id=prompt_id,
            task_id=task_id,
            approval_id=approval_id,
            provider=provider,
            model=model,
            verdict=verdict,
            reason=reason,
            risk_level=risk_level,
            metadata=metadata or {},
        )
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
        return event

    def tail(self, limit: int = 200) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows = []
        for line in self.path.read_text(encoding="utf-8").splitlines()[-limit:]:
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
        return rows
