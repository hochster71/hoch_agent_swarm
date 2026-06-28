from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any
import json
from pathlib import Path
from uuid import uuid4

class RuntimeProcessType(str, Enum):
    AGENT_TASK = "AGENT_TASK"
    MODEL_ROUTE = "MODEL_ROUTE"
    LOCAL_MODEL_HEALTH = "LOCAL_MODEL_HEALTH"
    LOCAL_ARBITRATION = "LOCAL_ARBITRATION"
    ESCALATION_RECOMMENDED = "ESCALATION_RECOMMENDED"
    ESCALATION_REQUESTED = "ESCALATION_REQUESTED"
    ESCALATION_APPROVAL_REQUIRED = "ESCALATION_APPROVAL_REQUIRED"
    ESCALATION_APPROVED = "ESCALATION_APPROVED"
    ESCALATION_DENIED = "ESCALATION_DENIED"
    GOOGLE_FRONTIER_CALL = "GOOGLE_FRONTIER_CALL"
    EVIDENCE_LEDGER_COMMIT = "EVIDENCE_LEDGER_COMMIT"
    GOVERNANCE_GATE = "GOVERNANCE_GATE"
    QUEUE_PRESSURE = "QUEUE_PRESSURE"
    RELEASE_STATE = "RELEASE_STATE"

class RuntimeProcessState(str, Enum):
    LIVE = "LIVE"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    ARBITRATING = "ARBITRATING"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    BLOCKED = "BLOCKED"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"

@dataclass
class RuntimeProcessEvent:
    event_id: str
    timestamp: str
    process_type: str
    state: str
    agent_id: str | None
    task_id: str | None
    provider: str | None
    model: str | None
    confidence_score: float | None
    risk_level: str | None
    requires_approval: bool
    escalation_used: bool
    evidence_ref: str | None
    message: str
    metadata: dict[str, Any]

class RuntimeProcessBus:
    def __init__(self, path: str = "audit/runtime_process_events.jsonl") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(
        self,
        process_type: RuntimeProcessType,
        state: RuntimeProcessState,
        message: str,
        *,
        agent_id: str | None = None,
        task_id: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        confidence_score: float | None = None,
        risk_level: str | None = None,
        requires_approval: bool = False,
        escalation_used: bool = False,
        evidence_ref: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RuntimeProcessEvent:
        event = RuntimeProcessEvent(
            event_id=f"rpe-{uuid4()}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            process_type=process_type.value,
            state=state.value,
            agent_id=agent_id,
            task_id=task_id,
            provider=provider,
            model=model,
            confidence_score=confidence_score,
            risk_level=risk_level,
            requires_approval=requires_approval,
            escalation_used=escalation_used,
            evidence_ref=evidence_ref,
            message=message,
            metadata=metadata or {},
        )
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
        return event

    def tail(self, limit: int = 100) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        rows = []
        for line in lines[-limit:]:
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
        return rows
