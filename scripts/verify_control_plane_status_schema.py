#!/usr/bin/env python3
import os
import sys
import json
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATUS_FILE = ROOT / "has_live_project_tracker/data" / "control_plane_status.json"

def get_utc_now():
    return datetime.datetime.now(datetime.timezone.utc)

def parse_utc_str(ts_str):
    try:
        ts_iso = ts_str.rstrip("Z").split("+")[0]
        return datetime.datetime.fromisoformat(ts_iso).replace(tzinfo=datetime.timezone.utc)
    except Exception:
        return None

def verify():
    if not STATUS_FILE.exists():
        print(f"❌ Error: control_plane_status.json is missing at {STATUS_FILE}")
        sys.exit(1)
        
    try:
        with open(STATUS_FILE, "r") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error: Failed to parse control_plane_status.json: {e}")
        sys.exit(1)

    required_keys = [
        "schema_version",
        "source_of_truth",
        "system_of_record",
        "as_of",
        "expires_at",
        "max_age_seconds",
        "authority",
        "compute",
        "rung_state",
        "has",
        "hasf",
        "agents",
        "adapters",
        "models",
        "freshness",
        "zero_tolerance",
        "stale_or_missing",
        "closure_actions"
    ]
    
    missing = [k for k in required_keys if k not in data]
    if missing:
        print(f"❌ Error: Missing required top-level keys: {missing}")
        sys.exit(1)
        
    if data["schema_version"] != "1.0":
        print(f"❌ Error: Invalid schema_version: got={data['schema_version']}, expected=1.0")
        sys.exit(1)
        
    # Check expiration
    now = get_utc_now()
    expires_dt = parse_utc_str(data["expires_at"])
    if not expires_dt:
        print(f"❌ Error: Invalid expires_at format: {data['expires_at']}")
        sys.exit(1)
        
    if now > expires_dt:
        print(f"⚠️ Warning: Snapshot has EXPIRED! now={now.isoformat()}, expires_at={expires_dt.isoformat()}")
        # We exit with 0 if just validating schema structure, but we print state.
        state = "EXPIRED"
    else:
        state = "FRESH"
        
    print(f"🟢 Schema validation passed successfully. Contract state: {state}")
    sys.exit(0)

if __name__ == "__main__":
    verify()
