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
import hashlib
import shutil
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

    def _reconstruct_floor(self) -> Optional[Dict[str, int]]:
        """Rebuild the max-issued token per task from every durable source that records one.

        Sources (union, MAX per task):
          _fencing_tokens.bak     (may lag one write)
          _token_journal.jsonl    (append-only, written at ISSUE time -- authoritative)
          _lease_history.jsonl    (released leases)
          _terminal_ledger.jsonl  (committed terminals)
        Returns None only if NOTHING is recoverable, in which case the caller fails closed.
        """
        floor: Dict[str, int] = {}
        found = False

        bak = self.tokens_file.with_suffix(".bak")
        if bak.exists():
            try:
                d = json.loads(bak.read_text())
                if isinstance(d, dict):
                    found = True
                    for k, v in d.items():
                        floor[k] = max(floor.get(k, 0), int(v))
            except Exception:
                pass

        for name in ("_token_journal.jsonl", "_lease_history.jsonl", "_terminal_ledger.jsonl"):
            fp = self.dir / name
            if not fp.exists():
                continue
            for line in fp.read_text().splitlines():
                try:
                    r = json.loads(line)
                    t, tok = r.get("task_id"), r.get("fencing_token")
                    if t is not None and tok is not None:
                        found = True
                        floor[t] = max(floor.get(t, 0), int(tok))
                except Exception:
                    continue

        return floor if found else None

    def _journal_token(self, task_id: str, token: int) -> None:
        """Append-only record at ISSUE time so the floor is ALWAYS reconstructable."""
        try:
            with open(self.dir / "_token_journal.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({"task_id": task_id, "fencing_token": int(token),
                                    "issued_at": _iso(_now())}) + "\n")
        except OSError:
            pass

    def _next_token(self, task_id: str) -> int:
        lockpath = self.dir / "_fencing_tokens.lock"
        with self._token_lock:
            with open(lockpath, "a+") as lf:
                fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
                try:
                    # GROK-F5 (CONFIRMED): on ANY read/parse error this reset tokens={},
                    # silently WIPING every other task's monotonic counter -- so a corrupt
                    # file re-issued token 1 for tasks that were already at 5, and a stale
                    # worker's old token would validate again. Fencing must FAIL CLOSED:
                    # never reset the ledger, never re-issue a used token.
                    tokens = {}
                    if self.tokens_file.exists():
                        try:
                            tokens = json.loads(self.tokens_file.read_text())
                            if not isinstance(tokens, dict):
                                raise ValueError("tokens file is not an object")
                        except Exception as e:
                            # The .bak alone is NOT safe: it lags one write behind, so a task
                            # added since the last backup would VANISH and get token 1 again.
                            # Rebuild the monotonic floor from every durable source that
                            # records a token, taking the MAX per task. Never lose a floor.
                            tokens = self._reconstruct_floor()
                            if tokens is None:
                                raise RuntimeError(
                                    "FENCING_LEDGER_CORRUPT: cannot reconstruct the monotonic "
                                    "floor from any durable source; refusing to mint a token "
                                    "that could re-use a retired value (fail closed). "
                                    f"Repair {self.tokens_file}. cause={e}") from e

                    nxt = int(tokens.get(task_id, 0)) + 1
                    tokens[task_id] = nxt
                    # keep a good backup BEFORE replacing, so corruption is recoverable
                    if self.tokens_file.exists():
                        try:
                            shutil.copyfile(self.tokens_file, self.tokens_file.with_suffix(".bak"))
                        except OSError:
                            pass
                    tmp = self.tokens_file.with_name(
                        f"_fencing_tokens.{os.getpid()}.{uuid.uuid4().hex[:6]}.tmp")
                    tmp.write_text(json.dumps(tokens, indent=2))
                    os.replace(tmp, self.tokens_file)   # atomic
                    self._journal_token(task_id, nxt)   # durable floor, append-only
                    return nxt
                finally:
                    fcntl.flock(lf.fileno(), fcntl.LOCK_UN)

    def _path(self, task_id: str) -> Path:
        # GROK-F3 (CONFIRMED): character-stripping collided distinct task_ids onto ONE lock
        # file -- 'task/a' and 'taska' both became 'taska.lock', silently breaking mutual
        # exclusion between two DIFFERENT tasks. The path must be INJECTIVE. A digest of the
        # raw id guarantees that; the readable prefix is for humans only.
        safe = "".join(ch for ch in task_id if ch.isalnum() or ch in "-_.")[:40]
        digest = hashlib.sha256(task_id.encode("utf-8")).hexdigest()[:16]
        return self.dir / f"{safe}.{digest}.lock"

    def read_lease(self, task_id: str) -> Optional[Dict[str, Any]]:
        p = self._path(task_id)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text())
        except Exception:
            # GROK-F4 (CONFIRMED): an empty/corrupt lock file made read_lease return None,
            # so acquire_lease skipped recovery and then lost the O_EXCL create forever --
            # the task became permanently unacquirable (liveness deadlock). Surface
            # corruption instead of hiding it as "no lease".
            return {"__corrupt__": True, "task_id": task_id, "status": "CORRUPT"}

    def is_expired(self, lease: Dict[str, Any]) -> bool:
        try:
            return _parse(lease["expires_at"]) <= _now()
        except Exception:
            return True

    def acquire_lease(self, task_id: str, holder: str,
                      duration_seconds: int = DEFAULT_LEASE_SECONDS,
                      binding: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Acquire the lease for THIS task only. Never blocks on other tasks.

        ``binding`` (optional) stamps authority fields onto the durable lock record so
        the wall/API can observe authority_decision_id without retrofitting history.
        """
        p = self._path(task_id)
        existing = self.read_lease(task_id)

        if (existing and not existing.get("__corrupt__")
                and existing.get("status") == "ACTIVE" and not self.is_expired(existing)):
            return None                      # someone else legitimately holds THIS task

        if existing and existing.get("__corrupt__"):
            # GROK-F4 fix: a corrupt lock is recoverable, not fatal. Quarantine and reclaim.
            try:
                p.replace(p.with_suffix(f".corrupt.{uuid.uuid4().hex[:6]}"))
            except OSError:
                p.unlink(missing_ok=True)
            existing = None

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
        # Authority binding (fail-visible on wall if absent for active work)
        if binding:
            for k in (
                "authority_class", "authority_decision_id", "authority_status",
                "decision_digest", "dispatch_digest", "scheduler_instance_id",
                "decision_id", "task_digest",
            ):
                if k in binding and binding[k] is not None:
                    lease[k] = binding[k]
        # Atomic create: if another worker won the race, O_EXCL raises and we lose.
        try:
            fd = os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return None
        with os.fdopen(fd, "w") as f:
            json.dump(lease, f, indent=2)
        return lease

    def update_lease_binding(self, task_id: str, binding: Dict[str, Any]) -> bool:
        """Merge authority fields into an existing ACTIVE lease (after digest mint)."""
        p = self._path(task_id)
        lease = self.read_lease(task_id)
        if not lease or lease.get("__corrupt__") or lease.get("status") != "ACTIVE":
            return False
        for k, v in binding.items():
            if v is not None:
                lease[k] = v
        lease["heartbeat_at"] = _iso(_now())
        tmp = p.with_suffix(f".{uuid.uuid4().hex[:6]}.tmp")
        tmp.write_text(json.dumps(lease, indent=2))
        os.replace(tmp, p)
        return True

    # ---- FENCING ENFORCEMENT -------------------------------------------------
    # Minting a monotonic token is not enough: it must be CHECKED at the write
    # boundary. Without this, a stale worker whose lease expired (and was superseded
    # by a strictly greater token) can still commit a terminal result. Fencing tokens
    # that are never validated are decoration.

    def current_token(self, task_id: str) -> int:
        """Highest token ever minted for this task (durable across restarts)."""
        try:
            return int(json.loads(self.tokens_file.read_text()).get(task_id, 0))
        except Exception:
            return 0

    def validate_fence(self, task_id: str, fencing_token: int) -> bool:
        """STALE-WORKER-REJECTION: a write is valid only from the CURRENT highest token."""
        return int(fencing_token) >= self.current_token(task_id)

    def commit_terminal(self, task_id: str, lease_id: str, fencing_token: int,
                        status: str = "COMPLETED") -> tuple[bool, str]:
        """Guarded terminal transition. Rejects stale-fence writes and duplicate terminals."""
        term = self.dir / "_terminal_ledger.jsonl"

        # DUPLICATE-TERMINAL-CONTROL: a task may reach a terminal state exactly once.
        if term.exists():
            for line in term.read_text().splitlines():
                try:
                    if json.loads(line).get("task_id") == task_id:
                        return False, "DUPLICATE_TERMINAL_REJECTED"
                except json.JSONDecodeError:
                    pass

        # STALE-WORKER-REJECTION-CONTROL
        if not self.validate_fence(task_id, fencing_token):
            return False, (f"STALE_FENCE_REJECTED token={fencing_token} "
                           f"current={self.current_token(task_id)}")

        with open(term, "a", encoding="utf-8") as f:
            f.write(json.dumps({"task_id": task_id, "lease_id": lease_id,
                                "fencing_token": int(fencing_token), "status": status,
                                "committed_at": _iso(_now())}) + "\n")
        return True, "COMMITTED"

    def heartbeat(self, task_id: str, lease_id: str) -> bool:
        lease = self.read_lease(task_id)
        if not lease or lease.get("lease_id") != lease_id:
            return False
        lease["heartbeat_at"] = _iso(_now())
        self._path(task_id).write_text(json.dumps(lease, indent=2))
        return True

    def release_lease(self, task_id: str, lease_id: str, status: str = "RELEASED") -> bool:
        """Release THIS lease. Returns False if it could not be released.

        CALLERS MUST CHECK THE RETURN VALUE. The scheduler discarded it and then logged
        'RELEASED' to the ledger unconditionally -- so the ledger recorded success whether or
        not the lock file was ever removed. 256 acquired / 236 released in the ledger, while
        14 lock files sat on disk still marked ACTIVE. Every '0 leaked leases' measurement in
        Phases A, B and C came from an instrument that could not record a failure.
        A ledger that cannot record failure is not evidence. It is a decoration.
        """
        lease = self.read_lease(task_id)
        if not lease or lease.get("lease_id") != lease_id or lease.get("__corrupt__"):
            # STRANDED LOCK: the file exists but we cannot legitimately release it (mismatched
            # lease_id, corrupt, or already gone). Say so; never let the caller assume success.
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
