#!/usr/bin/env python3
"""HELM Continuous Monitoring — CONTINUOUS runner (ConMon · NIST SP 800-137).

`scripts/run_conmon.py` performs ONE assessment cycle and exits; continuity there depends
entirely on an external scheduler (launchd/cron) re-invoking it. THIS runner is the
in-process continuous loop: it re-derives control posture on a fixed interval, emits a
fresh evidence bundle under `docs/evidence/conmon/` every cycle, and writes a heartbeat so
"is ConMon actually running continuously?" is itself answerable from live evidence.

Per EDR-0005 it EMITS EVIDENCE ONLY — it never creates git commits and never mutates the
frozen runtime. No fake green: posture is whatever `assess()` computes each cycle.

Each cycle:
  1. run_conmon.run()   -> assess + coordination/security/conmon_status.json + drift + history
  2. emit_evidence()    -> docs/evidence/conmon/ bundle (json + md + control map + latest.json)
  3. heartbeat          -> coordination/security/conmon_heartbeat.json (pid, cycles, next_run)

Usage:
  python3 scripts/conmon_continuous.py                 # loop forever, 1800s interval
  python3 scripts/conmon_continuous.py --interval 600  # every 10 min
  python3 scripts/conmon_continuous.py --once          # single cycle (cron/verify mode)
  python3 scripts/conmon_continuous.py --max-cycles 3  # run N cycles then exit (tests)

Install as a persistent daemon (founder): deploy/com.hoch.helm-conmon-continuous.plist
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))  # allow `import backend.*` when run standalone

HEARTBEAT = ROOT / "coordination" / "security" / "conmon_heartbeat.json"

_STOP = False


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _install_signal_handlers() -> None:
    def _handle(signum, _frame):  # graceful shutdown between cycles
        global _STOP
        _STOP = True
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _handle)
        except (ValueError, OSError):
            pass  # e.g. running off the main thread (tests) — best effort


def _write_heartbeat(state: str, cycles: int, interval: int,
                     last: dict | None, next_run: str | None) -> None:
    HEARTBEAT.parent.mkdir(parents=True, exist_ok=True)
    beat = {
        "schema": "HELM_CONMON_HEARTBEAT_v1",
        "state": state,               # STARTING | RUNNING | STOPPED
        "pid": os.getpid(),
        "updated_at": _now(),
        "interval_seconds": interval,
        "cycles_completed": cycles,
        "last_cycle": last,           # summary of most recent assessment
        "next_run_at": next_run,
        "note": ("continuous evidence loop (NIST SP 800-137); emits evidence only, "
                 "never commits, never touches the frozen runtime"),
    }
    tmp = HEARTBEAT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(beat, indent=2) + "\n")
    os.replace(tmp, HEARTBEAT)  # atomic


def run_cycle(emit: bool = True) -> dict:
    """One full ConMon cycle. Returns the status snapshot summary."""
    from scripts.run_conmon import run as run_status
    snap = run_status()  # assess() + status snapshot + drift + history (authoritative)
    if emit:
        try:
            from backend.security.conmon_evidence import emit_evidence
            from backend.security.helm_conmon import POSTURE
            posture = json.loads(POSTURE.read_text())
            manifest = emit_evidence(posture)
            snap = {**snap, "evidence_bundle": manifest.get("bundle")}
        except Exception as e:  # evidence emission must never crash the monitor
            snap = {**snap, "evidence_error": str(e)[:160]}
    return snap


def loop(interval: int, max_cycles: int | None, emit: bool = True) -> int:
    _install_signal_handlers()
    cycles = 0
    _write_heartbeat("STARTING", cycles, interval, None, None)
    while not _STOP:
        snap = run_cycle(emit=emit)
        cycles += 1
        d = snap.get("drift", {}) or {}
        print(f"[{_now()}] ConMon cycle {cycles}: posture {snap.get('posture_percent')}% · "
              f"{snap.get('controls_assessed')} controls · high={snap.get('high_findings')} · "
              f"drift {d.get('posture_delta','—')}", flush=True)

        if max_cycles is not None and cycles >= max_cycles:
            _write_heartbeat("STOPPED", cycles, interval, snap, None)
            return 0
        if _STOP:
            break

        next_run = datetime.now(timezone.utc).timestamp() + interval
        next_iso = datetime.fromtimestamp(next_run, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        _write_heartbeat("RUNNING", cycles, interval, snap, next_iso)

        # sleep in short slices so a stop signal is honored promptly
        slept = 0.0
        while slept < interval and not _STOP:
            time.sleep(min(1.0, interval - slept))
            slept += 1.0

    _write_heartbeat("STOPPED", cycles, interval, None, None)
    print(f"[{_now()}] ConMon continuous runner stopped after {cycles} cycle(s).", flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="HELM ConMon continuous runner")
    ap.add_argument("--interval", type=int, default=1800,
                    help="seconds between cycles (default 1800 = 30 min)")
    ap.add_argument("--once", action="store_true", help="run a single cycle then exit")
    ap.add_argument("--max-cycles", type=int, default=None,
                    help="run N cycles then exit (default: run forever)")
    ap.add_argument("--no-evidence", action="store_true",
                    help="skip the docs/evidence bundle (status snapshot only)")
    args = ap.parse_args(argv)

    max_cycles = 1 if args.once else args.max_cycles
    return loop(interval=max(1, args.interval), max_cycles=max_cycles,
                emit=not args.no_evidence)


if __name__ == "__main__":
    raise SystemExit(main())
