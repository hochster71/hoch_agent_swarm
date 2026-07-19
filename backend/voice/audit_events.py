from __future__ import annotations

import json
import os
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[2]
AUDIT_LOG_FILE = Path(os.getenv("HELM_AUDIT_LOG_PATH", str(ROOT / "data/runtime/voice_command_audit.jsonl")))

def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def _compute_hash(data: Dict[str, Any]) -> str:
    # Serialize sorted keys to guarantee deterministic hashing
    serialized = json.dumps(data, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

def log_voice_audit_event(
    request_id: str,
    provider: str,
    actor_id: str,
    device_id_hash: str,
    intent: str,
    classification: str,
    auth_result: str,
    confirmation_result: str,
    exec_result: str,
    target_resource: str,
    response_status: str,
    correlation_id: str = "",
    redactions_applied: bool = True,
    evidence_class: str = "LIVE_PROVIDER",
    provider_observation: bool = True,
    eligible_for_live_control: bool = True
) -> str:
    """Appends a tamper-evident hashed audit event to the append-only log.

    Returns the logged event ID.
    """
    import sys
    # If running under pytest or explicitly marked HAF run, mark as synthetic genesis
    if "pytest" in sys.modules or os.environ.get("HAF_RUNNING") == "1":
        evidence_class = "SYNTHETIC_GENESIS"
        provider_observation = False
        eligible_for_live_control = False

    VALID_CLASSES = {
        "LIVE_PROVIDER",
        "SIMULATOR_PROVIDER",
        "SYNTHETIC_GENESIS",
        "TEST_FIXTURE",
        "HAF_PROBE",
        "REPLAY_FIXTURE"
    }
    if evidence_class not in VALID_CLASSES:
        raise ValueError(f"Invalid evidence_class: {evidence_class}")

    AUDIT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Acquire exclusive lock on the live log to serialize writes
    import fcntl
    lock_file = AUDIT_LOG_FILE.with_suffix(".lock")
    lock_fd = None
    try:
        lock_fd = os.open(lock_file, os.O_CREAT | os.O_WRONLY, 0o600)
        fcntl.flock(lock_fd, fcntl.LOCK_EX)

        # Read last event to get previous_event_hash
        prev_hash = "GENESIS"
        if AUDIT_LOG_FILE.exists():
            try:
                with open(AUDIT_LOG_FILE, "rb") as f:
                    f.seek(0, os.SEEK_END)
                    file_size = f.tell()
                    if file_size > 0:
                        # Check if file has a trailing newline
                        f.seek(file_size - 1, os.SEEK_SET)
                        last_byte = f.read(1)
                        has_trailing = last_byte == b"\n"
                        required_newlines = 2 if has_trailing else 1
                        
                        chunk_size = 4096
                        pos = file_size
                        buffer = bytearray()
                        last_line = b""
                        
                        while pos > 0:
                            read_len = min(chunk_size, pos)
                            pos -= read_len
                            f.seek(pos, os.SEEK_SET)
                            chunk = f.read(read_len)
                            buffer = bytearray(chunk) + buffer
                            
                            newline_count = buffer.count(b"\n")
                            if newline_count >= required_newlines or pos == 0:
                                parts = buffer.split(b"\n")
                                for part in reversed(parts):
                                    if part.strip():
                                        last_line = part.strip()
                                        break
                                if last_line:
                                    break
                        
                        # Enforce event-size maximum of 64 KiB (including terminating LF)
                        stored_len = len(last_line) + 1
                        if stored_len > 65536:
                            raise ValueError(f"Audit event size exceeds maximum limit of 64 KiB: {stored_len} bytes")
                        
                        if last_line:
                            try:
                                last_event = json.loads(last_line.decode("utf-8"))
                                if "event_hash" in last_event:
                                    prev_hash = last_event["event_hash"]
                            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                                raise ValueError(f"Malformed final audit line detected: {e}")
            except Exception as e:
                if isinstance(e, ValueError):
                    raise e
                pass

        event_id = f"VOICE-EVT-{hashlib.md5(f'{request_id}-{time_str()}'.encode()).hexdigest()[:12].upper()}"
        
        event_payload: Dict[str, Any] = {
            "event_id": event_id,
            "request_id": request_id,
            "timestamp": _now(),
            "provider": provider,
            "actor_id": actor_id,
            "device_id_hash": device_id_hash,
            "intent": intent,
            "classification": classification,
            "authorization_result": auth_result,
            "confirmation_result": confirmation_result,
            "execution_result": exec_result,
            "target_resource": target_resource,
            "correlation_id": correlation_id,
            "response_status": response_status,
            "redactions_applied": redactions_applied,
            "evidence_class": evidence_class,
            "provider_observation": provider_observation,
            "eligible_for_live_control": eligible_for_live_control,
            "previous_event_hash": prev_hash,
            "chain_epoch": 2,
            "schema_version": "1.0.0"
        }

        # Redact all string properties in payload
        from backend.voice.redaction import redact_sensitive_data
        for k, v in event_payload.items():
            if isinstance(v, str) and k not in ("event_id", "previous_event_hash", "evidence_class"):
                event_payload[k] = redact_sensitive_data(v)

        # Compute hash of the payload
        event_hash = _compute_hash(event_payload)
        event_payload["event_hash"] = event_hash

        # Enforce 64 KiB size limit (measured in actual encoded bytes + terminating LF)
        serialized_line = json.dumps(event_payload).encode("utf-8")
        stored_size = len(serialized_line) + 1
        if stored_size > 65536:
            raise ValueError(f"Audit event size exceeds maximum limit of 64 KiB: {stored_size} bytes")

        # Write to append-only log file
        with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event_payload) + "\n")
            
        return event_id
    finally:
        if lock_fd is not None:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                os.close(lock_fd)
            except Exception:
                pass

def time_str() -> str:
    return str(datetime.now(timezone.utc).timestamp())
