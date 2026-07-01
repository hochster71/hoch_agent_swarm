#!/usr/bin/env python3
import os
import sys
import json
import urllib.request
import urllib.error
import base64
import sqlite3
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, "..")
SOURCE_DB = os.path.join(PROJECT_ROOT, "has_live_project_tracker", "data", "global_project_registry.sqlite")
BACKUP_DIR = os.path.join(PROJECT_ROOT, "has_live_project_tracker", "backups")
SECRETS_PATH = os.path.join(os.path.expanduser("~"), ".hoch-secrets", "has-tracker.env")

# 1. Load credentials
user = "admin"
password = "change-this-password"
port = "3001"

if os.path.exists(SECRETS_PATH):
    try:
        with open(SECRETS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip()
                if k == "TRACKER_USER":
                    user = v
                elif k == "TRACKER_PASSWORD":
                    password = v
                elif k == "TRACKER_PORT":
                    port = v
    except Exception as e:
        print(f"Warning: Failed to load secrets: {e}", file=sys.stderr)

# 2. Query /api/disk endpoint
url = f"http://localhost:{port}/api/disk"
req = urllib.request.Request(url)
auth_str = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("utf-8")
req.add_header("Authorization", f"Basic {auth_str}")

try:
    with urllib.request.urlopen(req) as resp:
        disk_data = json.loads(resp.read().decode("utf-8"))
except Exception as e:
    print(f"ERROR: Failed to query /api/disk: {e}", file=sys.stderr)
    sys.exit(1)

snapshot_allowed = disk_data.get("snapshot_allowed", False)
disk_available = disk_data.get("disk_available", 0.0)

print(f"Disk status: available = {disk_available} GB, snapshot_allowed = {snapshot_allowed}")

# Guard checks: only proceed if snapshot_allowed is true AND disk free > 50 GB
if not snapshot_allowed:
    print("SNAPSHOT BLOCKED: /api/disk snapshot_allowed is False")
    sys.exit(0)

if disk_available <= 50.0:
    print(f"SNAPSHOT BLOCKED: Free disk space {disk_available} GB is <= 50 GB threshold")
    sys.exit(0)

# 3. Create Safe online SQLite backup
if not os.path.exists(SOURCE_DB):
    print(f"ERROR: Source SQLite DB not found at {SOURCE_DB}", file=sys.stderr)
    sys.exit(1)

os.makedirs(BACKUP_DIR, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
target_name = f"snapshot_{timestamp}.sqlite"
target_path = os.path.join(BACKUP_DIR, target_name)

try:
    print(f"Starting online SQLite backup of {SOURCE_DB} to {target_path}...")
    src_conn = sqlite3.connect(SOURCE_DB)
    dst_conn = sqlite3.connect(target_path)
    
    with dst_conn:
        src_conn.backup(dst_conn)
        
    dst_conn.close()
    src_conn.close()
    
    # Make snapshot read-only
    os.chmod(target_path, 0o444)
    print(f"Snapshot created successfully: {target_name}")
except Exception as e:
    print(f"ERROR during SQLite backup: {e}", file=sys.stderr)
    sys.exit(1)

# 4. Enforce Retention limits: max 10 snapshot files, max age 7 days
try:
    now_time = datetime.now()
    age_limit = now_time - timedelta(days=7)
    
    # Scan backups directory for snapshot files
    snapshots = []
    for f in os.listdir(BACKUP_DIR):
        if f.startswith("snapshot_") and f.endswith(".sqlite"):
            fpath = os.path.join(BACKUP_DIR, f)
            mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
            snapshots.append((fpath, mtime))
            
    # Delete older than 7 days
    active_snapshots = []
    for fpath, mtime in snapshots:
        if mtime < age_limit:
            print(f"Retention policy: deleting expired snapshot: {os.path.basename(fpath)} (older than 7 days)")
            try:
                os.remove(fpath)
            except Exception as e:
                print(f"Failed to delete {fpath}: {e}", file=sys.stderr)
        else:
            active_snapshots.append((fpath, mtime))
            
    # Enforce max 10 files limit (sort oldest first)
    active_snapshots.sort(key=lambda x: x[1])
    while len(active_snapshots) > 10:
        fpath, mtime = active_snapshots.pop(0)
        print(f"Retention policy: deleting oldest snapshot: {os.path.basename(fpath)} (exceeds max limit of 10)")
        try:
            os.remove(fpath)
        except Exception as e:
            print(f"Failed to delete {fpath}: {e}", file=sys.stderr)
            
except Exception as e:
    print(f"Warning: Failed to enforce snapshot retention limits: {e}", file=sys.stderr)

print("SQLite snapshot scheduler process finished.")
