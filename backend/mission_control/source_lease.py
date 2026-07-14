"""Source-tree coordination guard — a per-FILE lease for concurrent agents.

WHY THIS EXISTS
---------------
On 2026-07-14 a Claude agent and a Grok agent edited the same source files at the same time with no
mutual exclusion. It merged cleanly by luck. The AU-9 chain enforces a single writer on the EVIDENCE
plane; nothing did the same for the SOURCE tree. This is that missing guard.

SCOPE — stated honestly
-----------------------
A lease gives mutual exclusion ONLY to agents that acquire it. It cannot stop a non-participating
editor from writing to a file. That is why this module ships with TWO teeth:

  1. acquire()/release()  — mutual exclusion for cooperating agents (per file, never global).
  2. verify_no_clobber()  — content-hash detection: catches a write by a NON-holder after the fact.

The commit-boundary detector (detect_source_conflicts.py) is the fail-closed enforcement point that
every agent passes through regardless of whether it took a lease.

This reuses the exact, battle-tested mechanics of PerTaskLeaseManager (O_EXCL atomic create, monotonic
per-key fencing tokens, TTL reclaim that is NOT decorative, corrupt-lock quarantine, injective digest
paths). Those mechanics were hardened against real 4-worker concurrency; there is no reason to reinvent
them for files.
"""
from __future__ import annotations

import datetime
import fcntl
import hashlib
import json
import os
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LEASE_SECONDS = 1800          # 30 min — a source edit is longer-lived than a task dispatch


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _iso(dt: datetime.datetime) -> str:
    return dt.isoformat()


def _parse(ts: str) -> datetime.datetime:
    dt = datetime.datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    return dt.replace(tzinfo=datetime.timezone.utc) if dt.tzinfo is None else dt


def _sha256_file(p: Path) -> Optional[str]:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except Exception:
        return None


class SourceLeaseManager:
    """One lock record per source file. Unrelated files never contend."""

    _token_lock = threading.Lock()

    def __init__(self, lease_dir: Path | None = None, repo_root: Path | None = None):
        self.repo_root = Path(repo_root) if repo_root else ROOT
        self.dir = Path(lease_dir) if lease_dir else (self.repo_root / "coordination" / "source_leases")
        self.dir.mkdir(parents=True, exist_ok=True)
        self.tokens_file = self.dir / "_fencing_tokens.json"

    # ---- injective lock path (a file's identity is its repo-relative path) -----------
    def _norm(self, rel_path: str) -> str:
        # normalize so 'a/b.py', './a/b.py', 'a//b.py' map to one identity, but DISTINCT files stay distinct
        return str(Path(str(rel_path)).as_posix()).lstrip("./")

    def _path(self, rel_path: str) -> Path:
        rel = self._norm(rel_path)
        safe = "".join(ch if (ch.isalnum() or ch in "-_.") else "_" for ch in rel)[:48]
        digest = hashlib.sha256(rel.encode("utf-8")).hexdigest()[:16]   # INJECTIVE — no collisions
        return self.dir / f"{safe}.{digest}.lock"

    # ---- monotonic fencing token per file, durable, fail-closed ----------------------
    def _next_token(self, rel: str) -> int:
        lockpath = self.dir / "_fencing_tokens.lock"
        with self._token_lock:
            with open(lockpath, "a+") as lf:
                fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
                try:
                    tokens: Dict[str, int] = {}
                    if self.tokens_file.exists():
                        try:
                            tokens = json.loads(self.tokens_file.read_text())
                            if not isinstance(tokens, dict):
                                raise ValueError("tokens file is not an object")
                        except Exception:
                            # fail closed: rebuild the floor from the append-only journal, never reset to 0
                            tokens = self._reconstruct_floor()
                    nxt = int(tokens.get(rel, 0)) + 1
                    tokens[rel] = nxt
                    tmp = self.tokens_file.with_name(
                        f"_fencing_tokens.{os.getpid()}.{uuid.uuid4().hex[:6]}.tmp")
                    tmp.write_text(json.dumps(tokens, indent=2))
                    os.replace(tmp, self.tokens_file)
                    with open(self.dir / "_token_journal.jsonl", "a", encoding="utf-8") as jf:
                        jf.write(json.dumps({"path": rel, "fencing_token": nxt,
                                             "issued_at": _iso(_now())}) + "\n")
                    return nxt
                finally:
                    fcntl.flock(lf.fileno(), fcntl.LOCK_UN)

    def _reconstruct_floor(self) -> Dict[str, int]:
        floor: Dict[str, int] = {}
        jp = self.dir / "_token_journal.jsonl"
        if jp.exists():
            for line in jp.read_text().splitlines():
                try:
                    r = json.loads(line)
                    p, tok = r.get("path"), r.get("fencing_token")
                    if p is not None and tok is not None:
                        floor[p] = max(floor.get(p, 0), int(tok))
                except Exception:
                    continue
        return floor

    def current_token(self, rel_path: str) -> int:
        rel = self._norm(rel_path)
        try:
            return int(json.loads(self.tokens_file.read_text()).get(rel, 0))
        except Exception:
            return int(self._reconstruct_floor().get(rel, 0))

    def validate_fence(self, rel_path: str, fencing_token: int) -> bool:
        """A write is valid only from the CURRENT highest token. Stale writers are rejected."""
        return int(fencing_token) >= self.current_token(rel_path)

    # ---- read / expiry ---------------------------------------------------------------
    def read_lease(self, rel_path: str) -> Optional[Dict[str, Any]]:
        p = self._path(rel_path)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text())
        except Exception:
            return {"__corrupt__": True, "path": self._norm(rel_path), "status": "CORRUPT"}

    def is_expired(self, lease: Dict[str, Any]) -> bool:
        try:
            return _parse(lease["expires_at"]) <= _now()
        except Exception:
            return True

    # ---- acquire / release -----------------------------------------------------------
    def acquire(self, rel_path: str, holder: str,
                duration_seconds: int = DEFAULT_LEASE_SECONDS) -> Optional[Dict[str, Any]]:
        """Acquire the lease for THIS file only. Never blocks on other files.

        Records the file's current content sha256 so a later clobber by a non-holder is detectable.
        Returns None if another holder legitimately holds an unexpired lease on this file.
        """
        rel = self._norm(rel_path)
        p = self._path(rel)
        existing = self.read_lease(rel)

        if (existing and not existing.get("__corrupt__")
                and existing.get("status") == "ACTIVE" and not self.is_expired(existing)):
            return None                                  # someone else holds this file

        if existing and existing.get("__corrupt__"):
            try:
                p.replace(p.with_suffix(f".corrupt.{uuid.uuid4().hex[:6]}"))
            except OSError:
                p.unlink(missing_ok=True)
            existing = None

        if existing:
            p.unlink(missing_ok=True)                    # stale/expired/released -> reclaim this file only

        now = _now()
        lease = {
            "path": rel,
            "lease_id": f"srclease-{uuid.uuid4().hex[:8]}",
            "holder": holder,
            "agent_pid": os.getpid(),
            "fencing_token": self._next_token(rel),
            "content_sha256_at_acquire": _sha256_file(self.repo_root / rel),
            "acquired_at": _iso(now),
            "expires_at": _iso(now + datetime.timedelta(seconds=duration_seconds)),
            "status": "ACTIVE",
        }
        try:
            fd = os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY)     # atomic — loser gets FileExistsError
        except FileExistsError:
            return None
        with os.fdopen(fd, "w") as f:
            json.dump(lease, f, indent=2)
        return lease

    def release(self, rel_path: str, lease_id: str, status: str = "RELEASED") -> bool:
        """Release THIS lease. Returns False (without unlinking) on lease_id mismatch or corruption.
        Callers MUST check the return — a release that did not happen must never read as success."""
        lease = self.read_lease(rel_path)
        if not lease or lease.get("__corrupt__") or lease.get("lease_id") != lease_id:
            return False
        lease["status"] = status
        lease["released_at"] = _iso(_now())
        with open(self.dir / "_source_lease_history.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(lease) + "\n")
        self._path(rel_path).unlink(missing_ok=True)
        return True

    # ---- clobber detection (content hash) --------------------------------------------
    def verify_no_clobber(self, rel_path: str, lease_id: str) -> Tuple[bool, str]:
        """Detect a write by a NON-holder: the file's content sha differs from what it was, and the
        difference was not made under this lease. Fail-closed: if we cannot verify, we do NOT say OK."""
        lease = self.read_lease(rel_path)
        if not lease or lease.get("__corrupt__"):
            return False, "CONTRADICTED: lease missing or corrupt — cannot vouch for the file"
        if lease.get("lease_id") != lease_id:
            return False, "CONTRADICTED: lease_id mismatch — a different holder owns this file"
        now_sha = _sha256_file(self.repo_root / self._norm(rel_path))
        base = lease.get("content_sha256_at_acquire")
        expected = lease.get("content_sha256_expected", base)
        if now_sha == expected:
            return True, "clean"
        return False, (f"CLOBBER DETECTED: {self._norm(rel_path)} changed on disk "
                       f"(expected {str(expected)[:12]}, found {str(now_sha)[:12]}) — a write occurred "
                       f"that this lease did not record")

    def record_own_write(self, rel_path: str, lease_id: str) -> bool:
        """The holder tells the lease 'I just wrote this file' so its own edits are not mistaken for
        a clobber. Updates the expected content hash. Returns False if not the holder."""
        lease = self.read_lease(rel_path)
        if not lease or lease.get("__corrupt__") or lease.get("lease_id") != lease_id:
            return False
        lease["content_sha256_expected"] = _sha256_file(self.repo_root / self._norm(rel_path))
        lease["last_write_at"] = _iso(_now())
        self._path(rel_path).write_text(json.dumps(lease, indent=2))
        return True

    # ---- reclaim / list --------------------------------------------------------------
    def reclaim_expired(self, *, now=None) -> List[Dict[str, Any]]:
        """Reclaim file leases whose TTL expired. A crashed agent must not lock a file forever.
        Corrupt locks are quarantined, never silently skipped and never fatal."""
        reclaimed: List[Dict[str, Any]] = []
        for lock in sorted(self.dir.glob("*.lock")):
            if lock.name.startswith("_"):
                continue
            try:
                rec = json.loads(lock.read_text(encoding="utf-8"))
            except Exception:
                q = lock.with_suffix(".lock.corrupt")
                try:
                    lock.rename(q)
                    reclaimed.append({"path": lock.stem, "status": "CORRUPT_QUARANTINED",
                                      "quarantined_to": q.name})
                except Exception:
                    pass
                continue
            if str(rec.get("status", "")).upper() != "ACTIVE":
                continue
            if not self.is_expired(rec):
                continue
            rec["status"] = "TIMED_OUT"
            rec["reclaimed_at"] = _iso(_now())
            rec["reclaim_reason"] = "SOURCE_LEASE_TTL_EXPIRED"
            lock.unlink(missing_ok=True)
            reclaimed.append(rec)
        return reclaimed

    def active(self) -> List[Dict[str, Any]]:
        """Every currently-held, unexpired file lease. Multiple files may appear — that is the point."""
        out = []
        for p in sorted(self.dir.glob("*.lock")):
            if p.name.startswith("_"):
                continue
            try:
                l = json.loads(p.read_text())
            except Exception:
                continue
            if l.get("status") == "ACTIVE" and not self.is_expired(l):
                out.append(l)
        return out
