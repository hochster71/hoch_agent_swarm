"""HELM Kernel Lease Manager.

Manages atomic, time-bound worker execution leases with fcntl.flock advisory locking
and persistent inter-process lease state synchronization.
"""

import os
import json
import fcntl
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_LEASE_LOCK_PATH = ROOT / "coordination" / "governance" / "helm_worker_leases.lock"


class HELMLeaseManager:
    """Manages worker execution leases and lock boundaries across OS processes."""

    def __init__(self, lock_path: Optional[Path] = None):
        self.lock_path = lock_path or DEFAULT_LEASE_LOCK_PATH
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.lock_path.exists():
            self.lock_path.write_text("{}", encoding="utf-8")

    def _read_leases_under_lock(self, lock_file) -> Dict[str, Dict[str, Any]]:
        """Reads lease state under flock lock."""
        lock_file.seek(0)
        content = lock_file.read().strip()
        if not content:
            return {}
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {}

    def _write_leases_under_lock(self, lock_file, leases: Dict[str, Dict[str, Any]]):
        """Writes lease state under flock lock."""
        lock_file.seek(0)
        lock_file.truncate()
        lock_file.write(json.dumps(leases, indent=2))
        lock_file.flush()
        os.fsync(lock_file.fileno())

    def acquire_lease(
        self,
        mission_id: str,
        execution_id: str,
        worker_id: str,
        lease_ttl_seconds: int = 300
    ) -> Dict[str, Any]:
        """Acquires a time-bound lease under POSIX flock inter-process locking."""
        with open(self.lock_path, "r+", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                leases = self._read_leases_under_lock(lock_file)
                now = datetime.now(timezone.utc)
                
                # Check for existing active lease for mission
                existing = leases.get(mission_id)
                if existing:
                    expires_dt = datetime.fromisoformat(existing["expires_at"].replace("Z", "+00:00"))
                    if now < expires_dt and existing["worker_id"] != worker_id:
                        raise RuntimeError(f"Active lease held by {existing['worker_id']} until {existing['expires_at']}")

                lease_id = f"lease-{uuid.uuid4().hex[:12]}"
                expires_at = (now + timedelta(seconds=lease_ttl_seconds)).isoformat().replace("+00:00", "Z")

                lease_info = {
                    "lease_id": lease_id,
                    "mission_id": mission_id,
                    "execution_id": execution_id,
                    "worker_id": worker_id,
                    "acquired_at": now.isoformat().replace("+00:00", "Z"),
                    "expires_at": expires_at,
                    "ttl_seconds": lease_ttl_seconds,
                    "status": "ACTIVE"
                }

                leases[mission_id] = lease_info
                self._write_leases_under_lock(lock_file, leases)
                return lease_info
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def renew_lease(self, mission_id: str, lease_id: str, extend_seconds: int = 300) -> Dict[str, Any]:
        """Extends an active lease TTL."""
        with open(self.lock_path, "r+", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                leases = self._read_leases_under_lock(lock_file)
                lease = leases.get(mission_id)
                if not lease or lease["lease_id"] != lease_id:
                    raise KeyError(f"Lease {lease_id} not found for mission {mission_id}")

                now = datetime.now(timezone.utc)
                new_expires = (now + timedelta(seconds=extend_seconds)).isoformat().replace("+00:00", "Z")
                lease["expires_at"] = new_expires
                lease["ttl_seconds"] += extend_seconds
                leases[mission_id] = lease
                self._write_leases_under_lock(lock_file, leases)
                return lease
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def is_lease_active(self, mission_id: str, lease_id: str) -> bool:
        """Checks if a lease remains valid and unexpired."""
        with open(self.lock_path, "r", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_SH)
            try:
                leases = self._read_leases_under_lock(lock_file)
                lease = leases.get(mission_id)
                if not lease or lease["lease_id"] != lease_id:
                    return False

                now = datetime.now(timezone.utc)
                expires_dt = datetime.fromisoformat(lease["expires_at"].replace("Z", "+00:00"))
                return now < expires_dt
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
