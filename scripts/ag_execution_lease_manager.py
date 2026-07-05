#!/usr/bin/env python3
import os
import json
import uuid
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "has_live_project_tracker/data"
LEASES_FILE = DATA_DIR / "ag_execution_leases.json"
LOCK_FILE = DATA_DIR / "ag_execution_lock.json"

def get_utc_now():
    return datetime.datetime.now(datetime.timezone.utc)

def to_utc_str(dt):
    return dt.isoformat().replace("+00:00", "Z")

def parse_utc_str(ts_str):
    try:
        ts_iso = ts_str.rstrip("Z").split("+")[0]
        return datetime.datetime.fromisoformat(ts_iso).replace(tzinfo=datetime.timezone.utc)
    except Exception:
        return get_utc_now()

def load_json(path, default):
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return default

def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

class LeaseManager:
    def __init__(self):
        pass

    def acquire_lease(self, task_id: str, holder: str, duration_seconds: int = 600) -> dict:
        lock = load_json(LOCK_FILE, None)
        now = get_utc_now()
        
        # Check active lock
        if lock:
            exp = parse_utc_str(lock["expires_at"])
            if now < exp and lock["status"] == "ACTIVE":
                print(f"[-] Active lease exists for task {lock['task_id']} held by {lock['holder']}.")
                return None
            else:
                # Active lock has expired, mark as expired in history and release it
                print(f"[!] Active lease for task {lock['task_id']} expired. Clearing it.")
                self.release_lease(lock["lease_id"], status="EXPIRED")

        # Create new lease
        lease_id = f"lease-{uuid.uuid4().hex[:8]}"
        expires_at = now + datetime.timedelta(seconds=duration_seconds)
        
        lease = {
            "lease_id": lease_id,
            "task_id": task_id,
            "acquired_at": to_utc_str(now),
            "expires_at": to_utc_str(expires_at),
            "holder": holder,
            "status": "ACTIVE"
        }
        
        save_json(LOCK_FILE, lease)
        
        leases = load_json(LEASES_FILE, [])
        leases.append(lease)
        save_json(LEASES_FILE, leases)
        
        print(f"[+] Lease {lease_id} acquired for task {task_id} by {holder}.")
        return lease

    def release_lease(self, lease_id: str, status: str = "RELEASED") -> bool:
        lock = load_json(LOCK_FILE, None)
        if not lock or lock["lease_id"] != lease_id:
            return False
            
        lock["status"] = status
        lock["released_at"] = to_utc_str(get_utc_now())
        
        # Clear active lock file
        save_json(LOCK_FILE, None)
        
        # Update leases database
        leases = load_json(LEASES_FILE, [])
        for lease in leases:
            if lease["lease_id"] == lease_id:
                lease["status"] = status
                lease["released_at"] = lock["released_at"]
                break
        save_json(LEASES_FILE, leases)
        
        print(f"[+] Lease {lease_id} released with status {status}.")
        return True

    def check_stale_leases(self) -> list:
        """Find and expire stale active leases."""
        lock = load_json(LOCK_FILE, None)
        now = get_utc_now()
        released = []
        if lock and lock["status"] == "ACTIVE":
            exp = parse_utc_str(lock["expires_at"])
            if now >= exp:
                print(f"[!] Lease {lock['lease_id']} has timed out.")
                self.release_lease(lock["lease_id"], status="EXPIRED")
                released.append(lock["lease_id"])
        return released

    def recover_failed_lease(self, lease_id: str) -> bool:
        """Move a lease into RECOVERED status to unblock future executions."""
        leases = load_json(LEASES_FILE, [])
        found = False
        for lease in leases:
            if lease["lease_id"] == lease_id and lease["status"] in ["ACTIVE", "FAILED", "EXPIRED"]:
                lease["status"] = "RECOVERED"
                lease["recovered_at"] = to_utc_str(get_utc_now())
                found = True
                break
        if found:
            save_json(LEASES_FILE, leases)
            lock = load_json(LOCK_FILE, None)
            if lock and lock["lease_id"] == lease_id:
                save_json(LOCK_FILE, None)
            print(f"[+] Lease {lease_id} marked as RECOVERED.")
            return True
        return False

if __name__ == "__main__":
    lm = LeaseManager()
    lm.check_stale_leases()
