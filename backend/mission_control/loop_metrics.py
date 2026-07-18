"""Executive-loop instrumentation — continuous health telemetry.

HELM must SEE degradation before it becomes a runtime failure. On 2026-07-15 the loop
died on 'database is locked' (cycle 506) with NO warning, because nothing measured lock
contention. This module makes the loop measure itself every cycle:

  * scheduler health      — cycle latency, idle/active/error mix
  * retry / lock contention — every locked-retry the durability layer performs (the direct
                              leading indicator of the exact 2026-07-15 failure mode)
  * mission throughput    — tasks completed per minute
  * uptime / restarts     — how long this loop has run, how many times it has (re)booted

Design: an in-process singleton (the council daemon builds the scheduler and runs cycles
in ONE process), thread-safe (tasks dispatch concurrently at concurrency>1). Each cycle a
snapshot is written to coordination/council/loop_metrics.json and folded into the
append-only council heartbeat, so the telemetry rides the channels that already exist.
"""
from __future__ import annotations

import json
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "coordination" / "council" / "loop_metrics.json"
BOOT_COUNTER = ROOT / "coordination" / "council" / "loop_boot_counter.json"

# --- Degradation thresholds (leading indicators, tuned to trip BEFORE a hard failure) ---
LOCK_RETRY_WARN = 1.0    # avg locked-retries/cycle over the window -> DEGRADED
LOCK_RETRY_CRIT = 4.0    # -> AT_RISK (contention approaching the 30s-busy-timeout wall)
ERROR_RATE_WARN = 0.10   # fraction of recent cycles in ERROR -> DEGRADED
ERROR_RATE_CRIT = 0.30   # -> AT_RISK
LATENCY_SPIKE_MULT = 3.0 # latest cycle latency vs. rolling median -> DEGRADED
_WINDOW = 50             # rolling window (cycles)


class LoopMetrics:
    """Thread-safe counters for the executive loop. One instance per process."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._mono0 = time.monotonic()
        self._wall0 = time.time()
        # cumulative
        self.cycles = 0
        self.idle = 0
        self.active = 0
        self.error = 0
        self.dispatched = 0
        self.passed = 0
        self.failed = 0
        self.lock_retries = 0          # every retry attempt the durability layer made
        self.lock_wait_s = 0.0         # total seconds spent waiting on locks
        self.lock_by_op: Dict[str, int] = {}
        # rolling windows
        self.recent_cycle_seconds: Deque[float] = deque(maxlen=_WINDOW)
        self.recent_states: Deque[str] = deque(maxlen=_WINDOW)
        self.recent_lock_retries: Deque[int] = deque(maxlen=_WINDOW)
        self._cycle_lock_retries = 0   # accumulator, reset per cycle
        self.boot_count = 0

    # ---- recorders (called from the loop / durability layer) ----------------
    def mark_boot(self) -> int:
        """Call once when the loop starts. Persists a cross-process (re)boot counter so
        'how many times did this loop have to restart' is observable."""
        count = 1
        try:
            if BOOT_COUNTER.exists():
                count = int(json.loads(BOOT_COUNTER.read_text()).get("count", 0)) + 1
            BOOT_COUNTER.parent.mkdir(parents=True, exist_ok=True)
            BOOT_COUNTER.write_text(json.dumps({"count": count, "last_boot": _now()}))
        except Exception:
            pass
        with self._lock:
            self.boot_count = count
        return count

    def record_lock_retry(self, what: str, waited: float) -> None:
        with self._lock:
            self.lock_retries += 1
            self.lock_wait_s += max(0.0, waited)
            self._cycle_lock_retries += 1
            self.lock_by_op[what] = self.lock_by_op.get(what, 0) + 1

    def record_cycle(self, *, state: str, dispatched: int = 0, passed: int = 0,
                     failed: int = 0, seconds: float = 0.0) -> None:
        with self._lock:
            self.cycles += 1
            st = (state or "").upper()
            if st == "IDLE":
                self.idle += 1
            elif st == "ERROR":
                self.error += 1
            else:
                self.active += 1
            self.dispatched += dispatched
            self.passed += passed
            self.failed += failed
            self.recent_cycle_seconds.append(float(seconds))
            self.recent_states.append(st)
            self.recent_lock_retries.append(self._cycle_lock_retries)
            self._cycle_lock_retries = 0

    # ---- derived views ------------------------------------------------------
    def uptime_seconds(self) -> float:
        return time.monotonic() - self._mono0

    def throughput_per_min(self) -> float:
        up = self.uptime_seconds()
        if up < 2.0:  # too little elapsed time to be meaningful — avoid absurd spikes
            return 0.0
        return round(self.passed / (up / 60.0), 3)

    def _median(self, seq) -> float:
        vals = sorted(v for v in seq if v is not None)
        if not vals:
            return 0.0
        n = len(vals)
        return vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2.0

    def assess(self) -> Dict[str, Any]:
        """Degradation detector — HEALTHY / DEGRADED / AT_RISK, with reasons. Trips on the
        leading indicators (rising lock-retry rate, error-cycle rate, latency spikes) so
        HELM can act BEFORE a hard runtime failure."""
        with self._lock:
            recent = list(self.recent_states)
            retries = list(self.recent_lock_retries)
            lat = list(self.recent_cycle_seconds)
        reasons = []
        state = "HEALTHY"

        def escalate(to: str):
            nonlocal state
            order = {"HEALTHY": 0, "DEGRADED": 1, "AT_RISK": 2}
            if order[to] > order[state]:
                state = to

        n = len(recent)
        if n:
            err_rate = recent.count("ERROR") / n
            if err_rate >= ERROR_RATE_CRIT:
                escalate("AT_RISK"); reasons.append(f"error-cycle rate {err_rate:.0%} >= {ERROR_RATE_CRIT:.0%}")
            elif err_rate >= ERROR_RATE_WARN:
                escalate("DEGRADED"); reasons.append(f"error-cycle rate {err_rate:.0%} >= {ERROR_RATE_WARN:.0%}")
        if retries:
            avg_retry = sum(retries) / len(retries)
            if avg_retry >= LOCK_RETRY_CRIT:
                escalate("AT_RISK"); reasons.append(f"lock-retry rate {avg_retry:.1f}/cycle >= {LOCK_RETRY_CRIT}")
            elif avg_retry >= LOCK_RETRY_WARN:
                escalate("DEGRADED"); reasons.append(f"lock-retry rate {avg_retry:.1f}/cycle >= {LOCK_RETRY_WARN}")
        if len(lat) >= 5:
            med = self._median(lat[:-1])
            if med > 0 and lat[-1] >= med * LATENCY_SPIKE_MULT:
                escalate("DEGRADED"); reasons.append(f"cycle latency {lat[-1]:.1f}s >= {LATENCY_SPIKE_MULT}x median {med:.1f}s")

        return {"state": state, "reasons": reasons or ["nominal"]}

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            base = {
                "ts": _now(),
                "uptime_seconds": round(self.uptime_seconds(), 1),
                "boot_count": self.boot_count,
                "cycles": {"total": self.cycles, "idle": self.idle,
                           "active": self.active, "error": self.error},
                "missions": {"dispatched": self.dispatched, "passed": self.passed,
                             "failed": self.failed,
                             "throughput_per_min": self.throughput_per_min()},
                "lock_contention": {"retries_total": self.lock_retries,
                                    "wait_seconds_total": round(self.lock_wait_s, 2),
                                    "by_op": dict(self.lock_by_op)},
                "last_cycle_seconds": (self.recent_cycle_seconds[-1]
                                       if self.recent_cycle_seconds else None),
            }
        base["health"] = self.assess()
        return base

    def flush(self) -> Dict[str, Any]:
        """Write the current snapshot to disk (called each cycle). Returns it for the
        heartbeat so the same numbers land in both channels."""
        snap = self.snapshot()
        try:
            SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
            SNAPSHOT.write_text(json.dumps(snap, indent=2), encoding="utf-8")
        except Exception:
            pass
        return snap


def _now() -> str:
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


# Module singleton — one per process.
METRICS = LoopMetrics()


def get() -> LoopMetrics:
    return METRICS
