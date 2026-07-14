"""HJOS supervision daemon — single-instance, fail-closed, non-hanging.

The observer swarm is worthless if its supervisor can be duplicated, wedged,
or run without an audit trail. This module enforces:

  - SINGLE INSTANCE : a live pid holding the lock blocks a second daemon.
  - STALE RECOVERY  : a dead pid is recovered WITH provenance, never trusted.
  - NO OVERLAP      : a cycle already in flight is never re-entered.
  - NO HANG         : a wedged cycle times out and is counted as a failure.
  - FAIL CLOSED     : no ledger => no cycle. Invalid governance => no mutation.
  - APPEND ONLY     : a restart never rewrites the ledger it inherits.

The daemon has NO mutation authority of its own. It never enables quarantine;
it only reports what the governance gate says (which stays DENY until a
founder-approved authorizing_policy_id exists).
"""
from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from backend.jspace.quarantine import (
    _governance,
    _mutation_authorized,
    validate_governance,
)

LOCK_SCHEMA = "HJOS_DAEMON_LOCK_v1"
STATE_SCHEMA = "HJOS_DAEMON_STATE_v1"
PREFLIGHT_SCHEMA = "HJOS_DAEMON_PREFLIGHT_v1"

DEFAULT_CYCLE_TIMEOUT_S = 120.0
DEFAULT_MAX_CONSECUTIVE_FAILURES = 3


class DaemonLockError(RuntimeError):
    """A live daemon already holds the single-instance lock."""


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _pid_alive(pid: int) -> bool:
    """True only if the pid is a real, currently-existing process."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists, owned by someone else
    except OSError:
        return False
    return True


def _atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True, default=str)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass


class SingleInstanceLock:
    """PID lock. A live incumbent wins; a dead incumbent is recovered on the record."""

    def __init__(self, path: Path, *, instance_id: Optional[str] = None) -> None:
        self.path = Path(path)
        self.instance_id = instance_id or f"hjos-{uuid.uuid4().hex[:8]}"
        self.held = False
        self.recovered_stale: Optional[Dict[str, Any]] = None

    def read(self) -> Optional[dict]:
        if not self.path.exists():
            return None
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {"_unreadable": True}
        if not isinstance(data, dict):
            return {"_unreadable": True}
        return data

    def acquire(self) -> dict:
        cur = self.read()
        recovered: Optional[Dict[str, Any]] = None
        if cur is not None:
            if cur.get("_unreadable"):
                recovered = {
                    "stale_pid": None,
                    "stale_instance_id": None,
                    "reason": "LOCK_UNREADABLE",
                    "recovered_at": _now(),
                }
            else:
                pid = cur.get("pid")
                same_instance = cur.get("instance_id") == self.instance_id
                if _pid_alive(pid) and not same_instance:
                    raise DaemonLockError(
                        "DAEMON_ALREADY_RUNNING "
                        f"pid={pid} instance={cur.get('instance_id')} "
                        f"since={cur.get('acquired_at')}"
                    )
                if not _pid_alive(pid):
                    recovered = {
                        "stale_pid": pid,
                        "stale_instance_id": cur.get("instance_id"),
                        "reason": "PID_NOT_ALIVE",
                        "recovered_at": _now(),
                    }
        rec = {
            "schema": LOCK_SCHEMA,
            "pid": os.getpid(),
            "instance_id": self.instance_id,
            "host": socket.gethostname(),
            "acquired_at": _now(),
            "recovered_stale": recovered,
        }
        _atomic_write_json(self.path, rec)
        self.held = True
        self.recovered_stale = recovered
        return rec

    def release(self) -> None:
        cur = self.read()
        if cur and cur.get("instance_id") == self.instance_id:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass
        self.held = False


class HJOSDaemon:
    """Supervises HJOS observation cycles. Observes only; authorizes nothing."""

    def __init__(
        self,
        *,
        repo_root: Path,
        ledger_root: Path,
        lock_path: Optional[Path] = None,
        cycle_fn: Optional[Callable[..., Any]] = None,
        cycle_timeout_s: float = DEFAULT_CYCLE_TIMEOUT_S,
        instance_id: Optional[str] = None,
        max_consecutive_failures: int = DEFAULT_MAX_CONSECUTIVE_FAILURES,
    ) -> None:
        self.repo_root = Path(repo_root)
        self.ledger_root = Path(ledger_root)
        self.instance_id = instance_id or f"hjos-{uuid.uuid4().hex[:8]}"
        self.lock = SingleInstanceLock(
            Path(lock_path) if lock_path else self.ledger_root / "hjos_daemon.lock",
            instance_id=self.instance_id,
        )
        self.cycle_timeout_s = float(cycle_timeout_s)
        self.max_consecutive_failures = int(max_consecutive_failures)
        self._cycle_fn = cycle_fn
        self._busy = threading.Lock()
        self._inflight: Optional[threading.Thread] = None
        self.state_path = self.ledger_root / "daemon_state.json"
        self.log_path = self.ledger_root / "daemon.jsonl"
        # When there is no ledger to persist to, the failure count must still be
        # visible in-process — a fail-closed daemon that reports zero failures is
        # just a silent one.
        self._mem_state: Optional[Dict[str, Any]] = None

    # ---------------------------------------------------------------- state
    def _load_state(self) -> Dict[str, Any]:
        base = {
            "schema": STATE_SCHEMA,
            "cycles_run": 0,
            "consecutive_failures": 0,
            "last_status": None,
            "last_error": None,
            "last_cycle_at": None,
        }
        if not self.ledger_root.is_dir():
            if self._mem_state:
                base.update(self._mem_state)
            return base
        if not self.state_path.exists():
            return base
        try:
            st = json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            base["last_status"] = "STATE_UNREADABLE"
            return base
        if not isinstance(st, dict):
            return base
        base.update(st)
        return base

    def _save_state(self, st: Dict[str, Any]) -> None:
        if not self.ledger_root.is_dir():
            # fail closed: never conjure the ledger into existence, but do not
            # lose the fact that we refused.
            self._mem_state = dict(st)
            return
        st["schema"] = STATE_SCHEMA
        st["instance_id"] = self.instance_id
        st["pid"] = os.getpid()
        st["updated_at"] = _now()
        _atomic_write_json(self.state_path, st)

    def _log(self, row: Dict[str, Any]) -> None:
        if not self.ledger_root.is_dir():
            return
        row = {
            "schema": "HJOS_DAEMON_EVENT_v1",
            "instance_id": self.instance_id,
            "pid": os.getpid(),
            "observed_at": _now(),
            **row,
        }
        with self.log_path.open("a", encoding="utf-8") as f:  # append-only, never truncate
            f.write(json.dumps(row, sort_keys=True, default=str) + "\n")
            f.flush()
            os.fsync(f.fileno())

    def status(self) -> Dict[str, Any]:
        st = self._load_state()
        failures = int(st.get("consecutive_failures") or 0)
        return {
            "schema": STATE_SCHEMA,
            "instance_id": self.instance_id,
            "pid": os.getpid(),
            "cycles_run": int(st.get("cycles_run") or 0),
            "consecutive_failures": failures,
            "max_consecutive_failures": self.max_consecutive_failures,
            "degraded": failures > 0,
            "halted": failures >= self.max_consecutive_failures,
            "last_status": st.get("last_status"),
            "last_error": st.get("last_error"),
            "last_cycle_at": st.get("last_cycle_at"),
            "lock_held": self.lock.held,
            "promotion_authority": "NONE",
        }

    # ------------------------------------------------------------ lifecycle
    def start(self) -> dict:
        rec = self.lock.acquire()
        self._log({"event": "DAEMON_START", "recovered_stale": rec.get("recovered_stale")})
        return rec

    def stop(self) -> None:
        self._log({"event": "DAEMON_STOP"})
        self.lock.release()

    # ------------------------------------------------------------ preflight
    def preflight(self) -> Dict[str, Any]:
        """Fail-closed gate. No ledger => no cycle. Bad governance => no mutation."""
        reasons = []
        if not self.ledger_root.exists() or not self.ledger_root.is_dir():
            reasons.append("LEDGER_MISSING")
        elif not os.access(str(self.ledger_root), os.W_OK):
            reasons.append("LEDGER_NOT_WRITABLE")

        gov = _governance(self.repo_root)
        gov_check = validate_governance(gov)
        if not gov_check["valid"]:
            reasons.extend(f"GOVERNANCE_{r}" for r in gov_check["reasons"])

        mutation_authorized = bool(
            gov_check["valid"] and _mutation_authorized(gov, kind="class_quarantine")
        )
        ok = not reasons
        return {
            "schema": PREFLIGHT_SCHEMA,
            "ok": ok,
            "fail_closed": not ok,
            "reasons": reasons,
            "mutation_authorized": mutation_authorized,
            "governance": gov_check,
            "ledger_root": str(self.ledger_root),
            "checked_at": _now(),
        }

    # ---------------------------------------------------------------- cycle
    def _resolve_cycle_fn(self) -> Callable[..., Any]:
        if self._cycle_fn is not None:
            return self._cycle_fn
        from backend.jspace.runner import run_hjos_cycle  # lazy: avoids import cycle
        return run_hjos_cycle

    def run_cycle(self) -> Dict[str, Any]:
        pf = self.preflight()
        if not pf["ok"]:
            st = self._load_state()
            st["consecutive_failures"] = int(st.get("consecutive_failures") or 0) + 1
            st["last_status"] = "FAIL_CLOSED"
            st["last_error"] = ";".join(pf["reasons"])
            st["last_cycle_at"] = _now()
            self._save_state(st)
            self._log({"event": "CYCLE_FAIL_CLOSED", "reasons": pf["reasons"]})
            return {
                "schema": "HJOS_DAEMON_CYCLE_v1",
                "status": "FAIL_CLOSED",
                "cycle_ran": False,
                "reasons": pf["reasons"],
                "consecutive_failures": int(st["consecutive_failures"]),
            }

        if self._inflight is not None and self._inflight.is_alive():
            self._log({"event": "CYCLE_SKIPPED", "reason": "PREVIOUS_CYCLE_STILL_RUNNING"})
            return {
                "schema": "HJOS_DAEMON_CYCLE_v1",
                "status": "SKIPPED_OVERLAP",
                "reason": "PREVIOUS_CYCLE_STILL_RUNNING",
                "cycle_ran": False,
            }
        if not self._busy.acquire(blocking=False):
            self._log({"event": "CYCLE_SKIPPED", "reason": "CYCLE_IN_PROGRESS"})
            return {
                "schema": "HJOS_DAEMON_CYCLE_v1",
                "status": "SKIPPED_OVERLAP",
                "reason": "CYCLE_IN_PROGRESS",
                "cycle_ran": False,
            }

        try:
            fn = self._resolve_cycle_fn()
            box: Dict[str, Any] = {}

            def _run() -> None:
                try:
                    box["result"] = fn(
                        repo_root=self.repo_root,
                        ledger_root=self.ledger_root,
                    )
                except TypeError:
                    try:
                        box["result"] = fn()
                    except Exception as e:  # noqa: BLE001
                        box["error"] = f"{type(e).__name__}: {e}"
                except Exception as e:  # noqa: BLE001
                    box["error"] = f"{type(e).__name__}: {e}"

            t = threading.Thread(target=_run, name=f"hjos-cycle-{self.instance_id}", daemon=True)
            started = time.time()
            t.start()
            t.join(self.cycle_timeout_s)

            st = self._load_state()
            st["cycles_run"] = int(st.get("cycles_run") or 0) + 1
            st["last_cycle_at"] = _now()

            if t.is_alive():
                # do NOT hang, and do NOT pretend it finished. Track the zombie so
                # the next tick cannot overlap it.
                self._inflight = t
                st["consecutive_failures"] = int(st.get("consecutive_failures") or 0) + 1
                st["last_status"] = "TIMEOUT"
                st["last_error"] = f"cycle exceeded {self.cycle_timeout_s}s"
                self._save_state(st)
                self._log({"event": "CYCLE_TIMEOUT", "timeout_s": self.cycle_timeout_s})
                return {
                    "schema": "HJOS_DAEMON_CYCLE_v1",
                    "status": "TIMEOUT",
                    "cycle_ran": False,
                    "timeout_s": self.cycle_timeout_s,
                    "elapsed_s": round(time.time() - started, 3),
                    "consecutive_failures": int(st["consecutive_failures"]),
                }

            if "error" in box:
                st["consecutive_failures"] = int(st.get("consecutive_failures") or 0) + 1
                st["last_status"] = "ERROR"
                st["last_error"] = box["error"]
                self._save_state(st)
                self._log({"event": "CYCLE_ERROR", "error": box["error"]})
                return {
                    "schema": "HJOS_DAEMON_CYCLE_v1",
                    "status": "ERROR",
                    "cycle_ran": False,
                    "error": box["error"],
                    "consecutive_failures": int(st["consecutive_failures"]),
                }

            st["consecutive_failures"] = 0
            st["last_status"] = "OK"
            st["last_error"] = None
            self._save_state(st)
            self._log({"event": "CYCLE_OK", "elapsed_s": round(time.time() - started, 3)})
            return {
                "schema": "HJOS_DAEMON_CYCLE_v1",
                "status": "OK",
                "cycle_ran": True,
                "elapsed_s": round(time.time() - started, 3),
                "consecutive_failures": 0,
                "result": box.get("result"),
            }
        finally:
            self._busy.release()
