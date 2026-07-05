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
    
    args = parser.parse_args()
    
    if not args.enable and not args.disable:
        # Just show status
        if HOLD_FILE.exists():
            with open(HOLD_FILE, "r") as f:
                data = json.load(f)
            print(f"Operator Hold Status: {'ACTIVE' if data.get('operator_hold_active') else 'INACTIVE'}")
            print(f"Reason: {data.get('reason')}")
            print(f"Operator: {data.get('operator')}")
            print(f"Timestamp: {data.get('timestamp')}")
            print(f"Affected Categories: {data.get('affected_categories')}")
        else:
            print("Operator hold file does not exist.")
        sys.exit(0)
        
    active = True if args.enable else False
    categories = [c.strip() for c in args.categories.split(",") if c.strip()]
    
    payload = {
        "operator_hold_active": active,
        "reason": args.reason,
        "operator": args.operator,
        "timestamp": get_utc_now(),
        "affected_categories": categories
    }
    
    HOLD_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HOLD_FILE, "w") as f:
        json.dump(payload, f, indent=2)
        
    print(f"🟢 Operator hold successfully updated to: {'ACTIVE' if active else 'INACTIVE'}")

if __name__ == "__main__":
    main()
