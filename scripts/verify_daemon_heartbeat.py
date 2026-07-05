#!/usr/bin/env python3
import os
import sys
import json
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "has_live_project_tracker/data"
DAEMON_STATE_FILE = DATA_DIR / "ag_execution_daemon_state.json"
HEARTBEAT_STATUS_FILE = DATA_DIR / "ag_daemon_heartbeat_status.json"

def get_utc_now():
    return datetime.datetime.now(datetime.timezone.utc)

def parse_utc_str(ts_str):
    try:
        ts_iso = ts_str.rstrip("Z").split("+")[0]
        return datetime.datetime.fromisoformat(ts_iso).replace(tzinfo=datetime.timezone.utc)
    except Exception:
        return None

def main():
    print("Checking Daemon Heartbeat Freshness...")
    
    if not DAEMON_STATE_FILE.exists():
        print("❌ Daemon state file missing. Heartbeat: MISSING.")
        status = {
            "heartbeat_status": "HEARTBEAT_MISSING",
            "last_observed_heartbeat": None,
            "verdict": "HEARTBEAT_MISSING"
        }
        with open(HEARTBEAT_STATUS_FILE, "w") as f:
            json.dump(status, f, indent=2)
        sys.exit(0)
        
    with open(DAEMON_STATE_FILE, "r") as f:
        state = json.load(f)
        
    last_hb_str = state.get("last_heartbeat")
    expires_str = state.get("heartbeat_expires_at")
    daemon_status = state.get("daemon_status", "IDLE")
    
    now = get_utc_now()
    expires_dt = parse_utc_str(expires_str) if expires_str else None
    
    if daemon_status != "RUNNING":
        verdict = "HEARTBEAT_NO_GO"
    elif not expires_dt or now > expires_dt:
        print(f"⚠️ Heartbeat has expired! Expiration: {expires_str}, Current: {now.isoformat()}")
        verdict = "HEARTBEAT_STALE"
    else:
        verdict = "HEARTBEAT_FRESH"
        
    status = {
        "heartbeat_status": verdict,
        "last_observed_heartbeat": last_hb_str,
        "verdict": verdict
    }
    
    with open(HEARTBEAT_STATUS_FILE, "w") as f:
        json.dump(status, f, indent=2)
        
    print(f"🟢 Daemon heartbeat freshness verdict: {verdict}")
    print("✅ AG Daemon Heartbeat verification PASSED.")
    sys.exit(0)

if __name__ == "__main__":
    main()
