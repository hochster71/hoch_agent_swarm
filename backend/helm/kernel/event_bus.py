"""HELM Kernel Event Bus & Replay Engine.

Implements an append-only, SHA256-chained JSONL event store, versioned event schemas,
checkpointing/snapshotting, metadata-certified multi-projection read models, and a deterministic event replay engine.
"""

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_EVENT_LOG_PATH = ROOT / "coordination" / "governance" / "helm_kernel_event_log.jsonl"
SUPPORTED_SCHEMA_VERSIONS = {"1.0", "1.1"}


def reject_duplicate_keys(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
    """RFC 8785 / I-JSON compliant duplicate property rejection at parse time."""
    seen = set()
    d = {}
    for key, val in pairs:
        if key in seen:
            raise ValueError(f"Duplicate key rejected under I-JSON rules: {key}")
        seen.add(key)
        d[key] = val
    return d


def canonical_json_bytes(obj: Any) -> bytes:
    """RFC 8785 canonical JSON serialization."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


class HELMEventBus:
    """Append-Only Event Store & Multi-Projection Replay Engine."""

    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = log_path or DEFAULT_EVENT_LOG_PATH
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def publish_event(
        self,
        event_type: str,
        mission_id: str,
        execution_id: str,
        actor: str,
        previous_state: str,
        new_state: str,
        payload: Optional[Dict[str, Any]] = None,
        artifact_hash: Optional[str] = None,
        event_id: Optional[str] = None,
        schema_version: str = "1.1",
        event_version: str = "1.0",
    ) -> Dict[str, Any]:
        """Appends a canonical event to the immutable JSONL event store."""
        if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
            raise ValueError(f"UNSUPPORTED_SCHEMA_VERSION: Schema version '{schema_version}' is not supported")

        payload = payload or {}
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        evt_id = event_id or f"evt-{hashlib.sha256(f'{now_iso}:{mission_id}:{event_type}'.encode()).hexdigest()[:12]}"

        # Compute previous hash in chain
        prev_hash = "GENESIS"
        if self.log_path.exists() and self.log_path.stat().st_size > 0:
            lines = self.log_path.read_text(encoding="utf-8").strip().splitlines()
            if lines:
                last_record = json.loads(lines[-1], object_pairs_hook=reject_duplicate_keys)
                prev_hash = last_record.get("event_hash", "GENESIS")

        event_data = {
            "schema_version": schema_version,
            "event_version": event_version,
            "event_id": evt_id,
            "timestamp": now_iso,
            "mission": mission_id,
            "execution_id": execution_id,
            "event_type": event_type,
            "actor": actor,
            "previous_state": previous_state,
            "new_state": new_state,
            "payload": payload,
            "artifact_hash": artifact_hash,
            "previous_event_hash": prev_hash,
        }

        # Calculate canonical SHA256 event hash
        event_bytes = canonical_json_bytes(event_data)
        event_hash = hashlib.sha256(event_bytes).hexdigest()
        event_data["event_hash"] = event_hash

        # Append to log under filesystem write
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event_data, sort_keys=True) + "\n")

        return event_data

    def read_event_stream(self) -> List[Dict[str, Any]]:
        """Reads all events from the event log with strict integrity and schema verification."""
        if not self.log_path.exists() or self.log_path.stat().st_size == 0:
            return []

        events = []
        seen_event_ids: Set[str] = set()
        expected_prev_hash = "GENESIS"

        for idx, line in enumerate(self.log_path.read_text(encoding="utf-8").splitlines()):
            if not line.strip():
                continue
            try:
                rec = json.loads(line, object_pairs_hook=reject_duplicate_keys)
            except Exception as e:
                raise ValueError(f"MALFORMED_JSON_EVENT: Event record at index {idx} is malformed JSON: {e}")

            # Check schema version compatibility
            s_ver = rec.get("schema_version", "1.0")
            if s_ver not in SUPPORTED_SCHEMA_VERSIONS:
                raise ValueError(f"UNSUPPORTED_SCHEMA_VERSION: Event record at index {idx} has unsupported schema version '{s_ver}'")

            # Check duplicate event_id
            e_id = rec.get("event_id")
            if not e_id or e_id in seen_event_ids:
                raise ValueError(f"DUPLICATE_EVENT_ID_REJECTED: Duplicate or missing event_id '{e_id}' at index {idx}")
            seen_event_ids.add(e_id)

            # Verify chain hash continuity
            if rec.get("previous_event_hash") != expected_prev_hash:
                raise ValueError(f"HASH_CHAIN_DISCONTINUITY: Event log hash chain discontinuity at index {idx}")
            
            rec_copy = dict(rec)
            actual_hash = rec_copy.pop("event_hash")
            computed_hash = hashlib.sha256(canonical_json_bytes(rec_copy)).hexdigest()
            if computed_hash != actual_hash:
                raise ValueError(f"EVENT_HASH_MISMATCH: Event record hash mismatch at index {idx}")

            expected_prev_hash = actual_hash
            events.append(rec)

        return events

    def save_checkpoint(self, checkpoint_path: Path) -> Dict[str, Any]:
        """Saves current state projection snapshot to a checkpoint file."""
        multi = self.replay_multi_projections()
        events = self.read_event_stream()
        last_hash = events[-1]["event_hash"] if events else "GENESIS"
        checkpoint_data = {
            "checkpoint_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "event_count": len(events),
            "last_event_hash": last_hash,
            "projections": multi["mission_projection"]["data"]
        }
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_path.write_text(json.dumps(checkpoint_data, indent=2, sort_keys=True), encoding="utf-8")
        return checkpoint_data

    def _build_projection_metadata(self, name: str, data: Any, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Constructs explicit projection metadata containing SHA256 integrity hash and event offsets."""
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        last_hash = events[-1]["event_hash"] if events else "GENESIS"
        last_offset = len(events) - 1 if events else 0
        data_hash = hashlib.sha256(canonical_json_bytes(data)).hexdigest()

        return {
            "name": name,
            "version": "1.0",
            "last_event_offset": last_offset,
            "last_event_hash": last_hash,
            "generated_at": now_iso,
            "projection_hash": data_hash
        }

    def replay_multi_projections(self) -> Dict[str, Any]:
        """Generates 4 decoupled read model projections with explicit metadata blocks from the event log."""
        events = self.read_event_stream()
        
        mission_data: Dict[str, Dict[str, Any]] = {}
        evidence_data: Dict[str, List[Dict[str, Any]]] = {}
        scheduler_data: Dict[str, Any] = {"active_leases": {}, "worker_allocations": {}}
        telemetry_data: Dict[str, Any] = {"total_events": len(events), "event_type_counts": {}, "actors": set()}

        for evt in events:
            m_id = evt["mission"]
            e_type = evt["event_type"]
            actor = evt["actor"]

            # Telemetry Projection
            telemetry_data["event_type_counts"][e_type] = telemetry_data["event_type_counts"].get(e_type, 0) + 1
            telemetry_data["actors"].add(actor)

            # Mission Projection
            if m_id not in mission_data:
                mission_data[m_id] = {
                    "mission_id": m_id,
                    "current_state": "NEW",
                    "execution_id": None,
                    "owner": None,
                    "lease_id": None,
                    "progress": 0,
                    "attempts": 0,
                    "history": [],
                    "artifacts": [],
                    "evidence_manifests": [],
                    "last_updated": evt["timestamp"],
                }
            
            proj = mission_data[m_id]
            proj["current_state"] = evt["new_state"]
            proj["last_updated"] = evt["timestamp"]
            proj["history"].append(evt["event_id"])
            if evt["execution_id"]:
                proj["execution_id"] = evt["execution_id"]

            # Evidence Projection
            if m_id not in evidence_data:
                evidence_data[m_id] = []
            if evt.get("artifact_hash") or evt["payload"].get("manifest_sha256"):
                evidence_data[m_id].append({
                    "event_id": evt["event_id"],
                    "event_type": e_type,
                    "artifact_hash": evt.get("artifact_hash"),
                    "manifest_sha256": evt["payload"].get("manifest_sha256"),
                    "timestamp": evt["timestamp"]
                })

            # Scheduler Projection
            if e_type == "MISSION_ALLOCATED":
                proj["owner"] = actor
                proj["attempts"] += 1
                scheduler_data["worker_allocations"][m_id] = actor
            elif e_type == "LEASE_GRANTED":
                proj["lease_id"] = evt["payload"].get("lease_id")
                scheduler_data["active_leases"][m_id] = evt["payload"]
            elif e_type == "ARTIFACT_CREATED" and evt.get("artifact_hash"):
                proj["artifacts"].append({
                    "path": evt["payload"].get("file_path"),
                    "hash": evt["artifact_hash"]
                })
            elif e_type == "VERIFICATION_COMPLETED" and evt["payload"].get("manifest_sha256"):
                proj["evidence_manifests"].append(evt["payload"]["manifest_sha256"])

        telemetry_data["actors"] = sorted(list(telemetry_data["actors"]))

        return {
            "mission_projection": {
                "metadata": self._build_projection_metadata("MissionProjection", mission_data, events),
                "data": mission_data
            },
            "evidence_projection": {
                "metadata": self._build_projection_metadata("EvidenceProjection", evidence_data, events),
                "data": evidence_data
            },
            "scheduler_projection": {
                "metadata": self._build_projection_metadata("SchedulerProjection", scheduler_data, events),
                "data": scheduler_data
            },
            "telemetry_projection": {
                "metadata": self._build_projection_metadata("TelemetryProjection", telemetry_data, events),
                "data": telemetry_data
            }
        }

    def replay_mission_state_projection(self, mission_id: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Reconstructs Mission State projections purely by replaying the event log."""
        multi = self.replay_multi_projections()
        projections = multi["mission_projection"]["data"]
        if mission_id:
            return {mission_id: projections[mission_id]} if mission_id in projections else {}
        return projections
