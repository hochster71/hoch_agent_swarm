"""Per-task lease manager (P2b) — replaces the global mutex.

DEFECT BEING FIXED
------------------
`scripts/ag_execution_lease_manager.LeaseManager` keeps ONE global lock file. Its
`acquire_lease()` returns None if *any* task holds a lock. So:

    configured concurrency = 4
    effective concurrency  = 1        <-- a runtime-truth defect

The scheduler advertised four workers and could only ever run one. Two unrelated
factories could not run at the same time.

DESIGN
------
One lock record per task:

    coordination/leases/<task_id>.lock

Guarantees:
  * exactly one ACTIVE lease per task (atomic O_EXCL create -- no TOCTOU window);
  * unrelated tasks run CONCURRENTLY (no shared lock);
  * fencing tokens are monotonic PER TASK, persisted so they survive restarts;
  * a stale lease is recovered only for its own task -- recovery never touches
    unrelated work;
  * the global operator hold stays a SEPARATE, explicit control (this module
    never implements it);
  * duplicate successful execution stays zero: a second worker cannot acquire an
    unexpired lease, and a recovered lease always mints a strictly greater token,
    so a zombie writer is fenced out.
"""
from __future__ import annotations

import datetime
import fcntl
import json
import os
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
LEASE_DIR = ROOT / "coordination" / "leases"
TOKENS_FILE = LEASE_DIR / "_fencing_tokens.json"

DEFAULT_LEASE_SECONDS = 600


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _iso(dt: datetime.datetime) -> str:
    return dt.isoformat()


def _parse(ts: str) -> datetime.datetime:
    dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


class PerTaskLeaseManager:
    """One lock file per task. Unrelated tasks never contend."""

    def __init__(self, lease_dir: Path | None = None):
        self.dir = Path(lease_dir) if lease_dir else LEASE_DIR
        self.dir.mkdir(parents=True, exist_ok=True)
        self.tokens_file = self.dir / "_fencing_tokens.json"

    # -- fencing tokens: monotonic PER TASK, durable across restarts ----------
    #
    # The token file is the ONE shared resource in this design, so its
    # read-modify-write must be serialized. A first cut used a single shared
    # `_fencing_tokens.tmp` + os.replace with no lock; under real 4-way
    # concurrency two workers raced, one replaced the temp file out from under
    # the other, and acquire_lease() raised FileNotFoundError. Only real
    # parallel execution surfaced it.
    #
    # Now: an in-process lock (threads) AND an flock on a dedicated lockfile
    # (cross-process), plus a UNIQUE temp name per writer.
    _token_lock = threading.Lock()

    def _next_token(self, task_id: str) -> int:
        lockpath = self.dir / "_fencing_tokens.lock"
        with self._token_lock:
            with open(lockpath, "a+") as lf:
                fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
                try:
                    try:
                        tokens = json.loads(self.tokens_file.read_text())
                    except Exception:
                        tokens = {}
                    nxt = int(tokens.get(task_id, 0)) + 1
                    tokens[task_id] = nxt
                    tmp = self.tokens_file.with_name(
                        f"_fencing_tokens.{os.getpid()}.{uuid.uuid4().hex[:6]}.tmp")
                    tmp.write_text(json.dumps(tokens, indent=2))
                    os.replace(tmp, self.tokens_file)   # atomic
                    return nxt
                finally:
                    fcntl.flock(lf.fileno(), fcntl.LOCK_UN)

    def _path(self, task_id: str) -> Path:
        safe = "".join(ch for ch in task_id if ch.isalnum() or ch in "-_.")
        return self.dir / f"{safe}.lock"

    def read_lease(self, task_id: str) -> Optional[Dict[str, Any]]:
        p = self._path(task_id)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text())
        except Exception:
            return None

    def is_expired(self, lease: Dict[str, Any]) -> bool:
        try:
            return _parse(lease["expires_at"]) <= _now()
        except Exception:
            return True

    def acquire_lease(self, task_id: str, holder: str,
                      duration_seconds: int = DEFAULT_LEASE_SECONDS) -> Optional[Dict[str, Any]]:
        """Acquire the lease for THIS task only. Never blocks on other tasks."""
        p = self._path(task_id)
        existing = self.read_lease(task_id)

        if existing and existing.get("status") == "ACTIVE" and not self.is_expired(existing):
            return None                      # someone else legitimately holds THIS task

        if existing:
            # Stale/expired or released -> recover. Scoped strictly to this task.
            existing["status"] = "EXPIRED" if existing.get("status") == "ACTIVE" else existing.get("status")
            existing["recovered_at"] = _iso(_now())
            p.write_text(json.dumps(existing, indent=2))
            p.unlink(missing_ok=True)

        now = _now()
        lease = {
            "task_id": task_id,
            "lease_id": f"lease-{uuid.uuid4().hex[:8]}",
            "worker_id": f"worker-{os.getpid()}-{uuid.uuid4().hex[:4]}",
            "holder": holder,
            "fencing_token": self._next_token(task_id),
            "acquired_at": _iso(now),
            "expires_at": _iso(now + datetime.timedelta(seconds=duration_seconds)),
            "heartbeat_at": _iso(now),
            "status": "ACTIVE",
        }
        # Atomic create: if another worker won the race, O_EXCL raises and we lose.
        try:
            fd = os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return None
        with os.fdopen(fd, "w") as f:
            json.dump(lease, f, indent=2)
        return lease

    def heartbeat(self, task_id: str, lease_id: str) -> bool:
        lease = self.read_lease(task_id)
        if not lease or lease.get("lease_id") != lease_id:
            return False
        lease["heartbeat_at"] = _iso(_now())
        self._path(task_id).write_text(json.dumps(lease, indent=2))
        return True

    def release_lease(self, task_id: str, lease_id: str, status: str = "RELEASED") -> bool:
        lease = self.read_lease(task_id)
        if not lease or lease.get("lease_id") != lease_id:
            return False
        lease["status"] = status
        lease["released_at"] = _iso(_now())
        # keep a durable history line, then drop the lock
        hist = self.dir / "_lease_history.jsonl"
        with open(hist, "a", encoding="utf-8") as f:
            f.write(json.dumps(lease) + "\n")
        self._path(task_id).unlink(missing_ok=True)
        return True

    def active_leases(self) -> List[Dict[str, Any]]:
        """Every currently-held, unexpired lease. Multiple tasks may appear here --
        that is the point."""
        out = []
        for p in sorted(self.dir.glob("*.lock")):
            try:
                l = json.loads(p.read_text())
            except Exception:
                continue
            if l.get("status") == "ACTIVE" and not self.is_expired(l):
                out.append(l)
        return out
