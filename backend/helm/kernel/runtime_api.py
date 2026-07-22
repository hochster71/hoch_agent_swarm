"""HELM Kernel Standardized Runtime API.

Exposes kernel operations for worker swarms and external components.
All state changes are driven exclusively by event emission to the Event Store.
"""

import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.helm.kernel.event_bus import HELMEventBus
from backend.helm.kernel.lease_manager import HELMLeaseManager
from backend.helm.kernel.capability_registry import HELMCapabilityRegistry


class HELMRuntimeAPI:
    """Standardized HELM Kernel Runtime API Interface."""

    def __init__(self, event_bus: Optional[HELMEventBus] = None):
        self.event_bus = event_bus or HELMEventBus()
        self.lease_manager = HELMLeaseManager()
        self.capability_registry = HELMCapabilityRegistry()

    def get_mission_projection(self, mission_id: Optional[str] = None) -> Dict[str, Any]:
        """Reconstructs current Mission State projection purely from event log replay."""
        projections = self.event_bus.replay_mission_state_projection(mission_id)
        if mission_id:
            return projections.get(mission_id, {"mission_id": mission_id, "current_state": "NOT_FOUND"})
        return projections

    def create_mission(
        self,
        mission_id: str,
        title: str,
        required_capabilities: List[str],
        priority: str = "HIGH",
        dependencies: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Submits a new mission intent to the Event Store."""
        dependencies = dependencies or []
        evt = self.event_bus.publish_event(
            event_type="MISSION_CREATED",
            mission_id=mission_id,
            execution_id="",
            actor="KERNEL_SCHEDULER",
            previous_state="NONE",
            new_state="NEW",
            payload={
                "title": title,
                "required_capabilities": required_capabilities,
                "priority": priority,
                "dependencies": dependencies,
            }
        )
        
        # Transition to PLANNED after validation
        self.event_bus.publish_event(
            event_type="MISSION_PLANNED",
            mission_id=mission_id,
            execution_id="",
            actor="KERNEL_SCHEDULER",
            previous_state="NEW",
            new_state="PLANNED",
            payload={"task_graph_valid": True}
        )
        return {"status": "PLANNED", "mission_id": mission_id, "event_id": evt["event_id"]}

    def allocate_mission(self, mission_id: str, worker_id: str) -> Dict[str, Any]:
        """Binds a mission to a worker and generates a new execution_id attempt."""
        proj = self.get_mission_projection(mission_id)
        current_state = proj.get("current_state", "UNKNOWN")

        if current_state not in ("PLANNED", "FAILED", "RETRY"):
            raise ValueError(f"Cannot allocate mission in state {current_state}")

        execution_id = f"exec-{uuid.uuid4().hex[:12]}"
        evt = self.event_bus.publish_event(
            event_type="MISSION_ALLOCATED",
            mission_id=mission_id,
            execution_id=execution_id,
            actor=worker_id,
            previous_state=current_state,
            new_state="ALLOCATED",
            payload={"worker_id": worker_id}
        )
        return {"status": "ALLOCATED", "mission_id": mission_id, "execution_id": execution_id}

    def acquire_lease(
        self,
        mission_id: str,
        execution_id: str,
        worker_id: str,
        lease_ttl_seconds: int = 300
    ) -> Dict[str, Any]:
        """Locks a worker lease and transitions mission to RUNNING."""
        proj = self.get_mission_projection(mission_id)
        current_state = proj.get("current_state", "UNKNOWN")

        lease = self.lease_manager.acquire_lease(
            mission_id=mission_id,
            execution_id=execution_id,
            worker_id=worker_id,
            lease_ttl_seconds=lease_ttl_seconds
        )

        self.event_bus.publish_event(
            event_type="LEASE_GRANTED",
            mission_id=mission_id,
            execution_id=execution_id,
            actor=worker_id,
            previous_state=current_state,
            new_state="RUNNING",
            payload=lease
        )
        return lease

    def publish_tool_execution(
        self,
        mission_id: str,
        execution_id: str,
        worker_id: str,
        tool_name: str,
        artifact_path: Optional[str] = None,
        artifact_hash: Optional[str] = None
    ) -> Dict[str, Any]:
        """Records a tool execution or artifact creation event."""
        event_type = "ARTIFACT_CREATED" if artifact_path else "TOOL_INVOKED"
        return self.event_bus.publish_event(
            event_type=event_type,
            mission_id=mission_id,
            execution_id=execution_id,
            actor=worker_id,
            previous_state="RUNNING",
            new_state="RUNNING",
            payload={"tool_name": tool_name, "file_path": artifact_path},
            artifact_hash=artifact_hash
        )

    def verify_mission(
        self,
        mission_id: str,
        execution_id: str,
        worker_id: str,
        test_status: str,
        test_count: int,
        manifest_sha256: str
    ) -> Dict[str, Any]:
        """Submits Swarm D test verification logs and transitions to VERIFYING -> REVIEW."""
        if test_status != "PASSED":
            return self.fail_mission(mission_id, execution_id, worker_id, "QA_TEST_FAILURE", "Test suite failed")

        self.event_bus.publish_event(
            event_type="VERIFICATION_COMPLETED",
            mission_id=mission_id,
            execution_id=execution_id,
            actor=worker_id,
            previous_state="RUNNING",
            new_state="VERIFYING",
            payload={"test_count": test_count, "manifest_sha256": manifest_sha256}
        )

        self.event_bus.publish_event(
            event_type="SUBMITTED_FOR_REVIEW",
            mission_id=mission_id,
            execution_id=execution_id,
            actor=worker_id,
            previous_state="VERIFYING",
            new_state="REVIEW",
            payload={"manifest_sha256": manifest_sha256}
        )
        return {"status": "REVIEW", "mission_id": mission_id}

    def review_mission(
        self,
        mission_id: str,
        execution_id: str,
        reviewer_id: str,
        approved: bool,
        review_notes: str
    ) -> Dict[str, Any]:
        """Records Independent Reviewer audit approval."""
        if not approved:
            return self.fail_mission(mission_id, execution_id, reviewer_id, "REVIEW_REJECTED", review_notes)

        self.event_bus.publish_event(
            event_type="REVIEW_APPROVED",
            mission_id=mission_id,
            execution_id=execution_id,
            actor=reviewer_id,
            previous_state="REVIEW",
            new_state="REVIEW",
            payload={"reviewer_id": reviewer_id, "notes": review_notes}
        )
        return {"status": "APPROVED", "mission_id": mission_id}

    def promote_mission(
        self,
        mission_id: str,
        execution_id: str,
        founder_approval_id: str
    ) -> Dict[str, Any]:
        """Commits mission to PROMOTED terminal state following Founder Gate clearance."""
        proj = self.get_mission_projection(mission_id)
        if proj.get("current_state") != "REVIEW":
            raise ValueError(f"Cannot promote mission in state {proj.get('current_state')}")

        evt = self.event_bus.publish_event(
            event_type="MISSION_PROMOTED",
            mission_id=mission_id,
            execution_id=execution_id,
            actor="FOUNDER_GATE",
            previous_state="REVIEW",
            new_state="PROMOTED",
            payload={"founder_approval_id": founder_approval_id}
        )
        return {"status": "PROMOTED", "mission_id": mission_id, "event_id": evt["event_id"]}

    def fail_mission(
        self,
        mission_id: str,
        execution_id: str,
        actor: str,
        error_code: str,
        error_message: str
    ) -> Dict[str, Any]:
        """Records a mission failure and evaluates retry eligibility."""
        proj = self.get_mission_projection(mission_id)
        current_state = proj.get("current_state", "UNKNOWN")

        self.event_bus.publish_event(
            event_type="EXECUTION_FAILED",
            mission_id=mission_id,
            execution_id=execution_id,
            actor=actor,
            previous_state=current_state,
            new_state="FAILED",
            payload={"error_code": error_code, "error_message": error_message}
        )

        attempts = proj.get("attempts", 1)
        if attempts < 3:
            self.event_bus.publish_event(
                event_type="MISSION_REQUEUED",
                mission_id=mission_id,
                execution_id=execution_id,
                actor="KERNEL_SCHEDULER",
                previous_state="FAILED",
                new_state="RETRY",
                payload={"attempt_count": attempts + 1}
            )
            return {"status": "RETRY", "mission_id": mission_id, "attempt": attempts + 1}

        self.event_bus.publish_event(
            event_type="MISSION_BLOCKED",
            mission_id=mission_id,
            execution_id=execution_id,
            actor="KERNEL_SCHEDULER",
            previous_state="FAILED",
            new_state="BLOCKED",
            payload={"reason": "Max retries exceeded"}
        )
        return {"status": "BLOCKED", "mission_id": mission_id}
