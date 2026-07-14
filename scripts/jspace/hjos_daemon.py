#!/usr/bin/env python3
"""HJOS periodic daemon — observe every N seconds.

Read-only by default. After burn-in, may execute charter-gated quarantine.
Does not compete with HELM for task dispatch or promotion.

Usage:
  .venv/bin/python scripts/jspace/hjos_daemon.py --interval 60
  nohup .venv/bin/python scripts/jspace/hjos_daemon.py --interval 60 > /tmp/hjos_daemon.log 2>&1 &
"""
from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

_STOP = False


def _handle(sig, frame):
    global _STOP
    _STOP = True


def main() -> int:
    ap = argparse.ArgumentParser(description="HJOS observability daemon")
    ap.add_argument("--interval", type=int, default=60, help="seconds between cycles")
    ap.add_argument("--once", action="store_true", help="single cycle then exit")
    ap.add_argument("--ledger", type=Path, default=None)
    ap.add_argument("--min-burn-in", type=int, default=5)
    args = ap.parse_args()

    signal.signal(signal.SIGTERM, _handle)
    signal.signal(signal.SIGINT, _handle)

    from backend.jspace.burn_in import BurnInTracker
    from backend.jspace.ledger import JSpaceLedger, DEFAULT_JSPACE_DIR
    from backend.jspace.runner import run_hjos_cycle

    ledger_root = args.ledger or DEFAULT_JSPACE_DIR
    # ensure min cycles on tracker
    BurnInTracker(ledger_root, min_cycles=args.min_burn_in)

    print(json.dumps({
        "event": "HJOS_DAEMON_START",
        "interval": args.interval,
        "ledger": str(ledger_root),
        "min_burn_in": args.min_burn_in,
    }), flush=True)

    while not _STOP:
        t0 = time.time()
        try:
            result = run_hjos_cycle(ledger_root=ledger_root)
            print(json.dumps({
                "event": "HJOS_CYCLE",
                "cycle_id": result["cycle_id"],
                "overall": result["overall"],
                "alerts": result["open_alerts"],
                "action": result["recommended_action"],
                "burn_in": result.get("burn_in"),
                "quarantine_executed": [
                    q for q in (result.get("quarantine_results") or []) if q.get("executed")
                ],
            }, default=str), flush=True)
        except Exception as e:
            print(json.dumps({
                "event": "HJOS_CYCLE_ERROR",
                "error": f"{type(e).__name__}: {e}",
            }), flush=True)
        if args.once:
            break
        elapsed = time.time() - t0
        sleep_for = max(1.0, args.interval - elapsed)
        # interruptible sleep
        end = time.time() + sleep_for
        while not _STOP and time.time() < end:
            time.sleep(min(1.0, end - time.time()))

    print(json.dumps({"event": "HJOS_DAEMON_STOP"}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
