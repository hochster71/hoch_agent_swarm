#!/usr/bin/env python3
import sys
import json
import datetime
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOLD_FILE = ROOT / "has_live_project_tracker/data/ag_operator_hold.json"

def get_utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

def main():
    parser = argparse.ArgumentParser(description="Operator Hold Control Switch")
    parser.add_argument("--enable", action="store_true", help="Enable operator hold")
    parser.add_argument("--disable", action="store_true", help="Disable operator hold")
    parser.add_argument("--reason", default="Manual operator intervention", help="Reason for hold status change")
    parser.add_argument("--operator", default="Michael Hoch", help="Operator name")
    parser.add_argument("--categories", default="", help="Comma separated categories affected")
    parser.add_argument("--class", dest="hold_class", default="manual",
                        help="Hold class: 'manual' (never auto-expires) or 'simulated'/'test' (auto-expires via TTL)")
    parser.add_argument("--ttl-seconds", type=int, default=0,
                        help="Auto-expiry seconds (0=none for manual; simulated holds default to 300s)")

    args = parser.parse_args()

    if not args.enable and not args.disable:
        # Just show status (effective, honoring TTL/expiry)
        if HOLD_FILE.exists():
            with open(HOLD_FILE, "r") as f:
                data = json.load(f)
            try:
                sys.path.insert(0, str(ROOT))
                from backend.runtime_truth.operator_hold import evaluate_hold
                ev = evaluate_hold(data)
                eff = ev["effective_active"]
                print(f"Operator Hold Status (effective): {'ACTIVE' if eff else 'INACTIVE'}")
                if ev["raw_active"] and ev["expired"]:
                    print(f"  (raw flag ACTIVE but auto-expired: class={ev['hold_class']}, expired_at={ev['expires_at']})")
            except Exception:
                print(f"Operator Hold Status: {'ACTIVE' if data.get('operator_hold_active') else 'INACTIVE'}")
            print(f"Reason: {data.get('reason')}")
            print(f"Operator: {data.get('operator')}")
            print(f"Class: {data.get('hold_class', 'manual')}")
            print(f"Timestamp: {data.get('timestamp')}")
            print(f"Expires At: {data.get('expires_at')}")
            print(f"Affected Categories: {data.get('affected_categories')}")
        else:
            print("Operator hold file does not exist.")
        sys.exit(0)

    active = True if args.enable else False
    categories = [c.strip() for c in args.categories.split(",") if c.strip()]

    # Resolve TTL: simulated/test holds get a default 300s TTL so they cannot
    # latch autonomy forever; manual holds only expire if a TTL is given.
    hold_class = (args.hold_class or "manual").lower()
    ttl = args.ttl_seconds
    if active and ttl == 0 and hold_class in ("simulated", "test", "chaos", "injected"):
        ttl = 300
    expires_at = None
    if active and ttl > 0:
        expires_at = (datetime.datetime.now(datetime.timezone.utc)
                      + datetime.timedelta(seconds=ttl)).isoformat().replace("+00:00", "Z")

    payload = {
        "operator_hold_active": active,
        "reason": args.reason,
        "operator": args.operator,
        "hold_class": hold_class,
        "timestamp": get_utc_now(),
        "expires_at": expires_at,
        "affected_categories": categories
    }
    
    HOLD_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HOLD_FILE, "w") as f:
        json.dump(payload, f, indent=2)
        
    EVENTS_FILE = ROOT / "has_live_project_tracker/data/ag_operator_hold_events.jsonl"
    with open(EVENTS_FILE, "a", encoding="utf-8") as ef:
        ef.write(json.dumps(payload) + "\n")
        
    print(f"🟢 Operator hold successfully updated to: {'ACTIVE' if active else 'INACTIVE'}")

if __name__ == "__main__":
    main()
