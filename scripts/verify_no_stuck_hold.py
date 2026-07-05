#!/usr/bin/env python3
"""Watchdog check: alert if an operator hold has been latched longer than its
class allows. Simulated/test holds should never outlive their TTL; a manual hold
older than --warn-hours is surfaced so a forgotten e-stop can't silently park the
fleet for days. Exit code 0 = OK, 2 = ALERT. Safe/read-only.
"""
import sys
import json
import datetime
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOLD_FILE = ROOT / "has_live_project_tracker/data/ag_operator_hold.json"
sys.path.insert(0, str(ROOT))


def main():
    ap = argparse.ArgumentParser(description="Alert on stuck operator holds")
    ap.add_argument("--warn-hours", type=float, default=6.0,
                    help="Warn if a manual hold has been active longer than this")
    args = ap.parse_args()

    if not HOLD_FILE.exists():
        print("OK: no hold file")
        return 0
    data = json.loads(HOLD_FILE.read_text())

    from backend.runtime_truth.operator_hold import evaluate_hold
    now = datetime.datetime.now(datetime.timezone.utc)
    ev = evaluate_hold(data, now=now)

    if not ev["raw_active"]:
        print("OK: hold inactive")
        return 0
    if ev["expired"]:
        print(f"ALERT: hold flagged active but auto-expired (class={ev['hold_class']}, "
              f"expired_at={ev['expires_at']}). Daemon treats it INACTIVE; clear the flag "
              f"with: python3 scripts/ag_operator_hold.py --disable")
        return 2

    ts = data.get("timestamp")
    try:
        age_h = (now - datetime.datetime.fromisoformat(str(ts).replace("Z", "+00:00"))).total_seconds() / 3600.0
    except Exception:
        age_h = None
    if age_h is not None and age_h > args.warn_hours and ev["hold_class"] == "manual":
        print(f"ALERT: manual hold active {age_h:.1f}h (> {args.warn_hours}h). "
              f"Operator={ev['operator']!r} reason={ev['reason']!r}. Confirm still intended.")
        return 2

    print(f"OK: hold active and within policy (class={ev['hold_class']}, age="
          f"{age_h:.1f}h)" if age_h is not None else "OK: hold active")
    return 0


if __name__ == "__main__":
    sys.exit(main())
