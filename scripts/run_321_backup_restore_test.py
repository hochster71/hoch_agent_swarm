#!/usr/bin/env python3
# scripts/run_321_backup_restore_test.py
import os
import sys
import json
import hashlib
import sqlite3
import tempfile
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCAL_BACKUP_DIR = ROOT / "data/backups/remote_vps"
TARGET_HOST = "100.87.18.15"
TARGET_USER = "root"

def compute_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def main():
    print("==================================================")
    print("RUNNING 3-2-1 BACKUP & RESTORE TEST SUITE")
    print("==================================================")
    
    # 1. Trigger remote backup
    print("[1] Triggering backup on remote host...")
    ssh_cmd = [
        "ssh", "-o", "StrictHostKeyChecking=accept-new",
        f"{TARGET_USER}@{TARGET_HOST}",
        "cd /root/hoch_agent_swarm && BACKUP_DIR=./deploy/remote-relay/backups bash deploy/remote-relay/backup.sh"
    ]
    res = subprocess.run(ssh_cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"❌ Remote backup failed: {res.stderr}")
        sys.exit(1)
    print(res.stdout.strip())
    
    # 2. Sync backup files off-box to local MacBook Pro
    print("\n[2] Downloading backup off-box to local MacBook (3-2-1)...")
    LOCAL_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    rsync_cmd = [
        "rsync", "-avz", "-e", "ssh -o StrictHostKeyChecking=accept-new",
        f"{TARGET_USER}@{TARGET_HOST}:/root/hoch_agent_swarm/deploy/remote-relay/backups/",
        str(LOCAL_BACKUP_DIR)
    ]
    res = subprocess.run(rsync_cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"❌ Failed to download backup files: {res.stderr}")
        sys.exit(1)
    
    # 3. Read manifest and verify checksum
    print("\n[3] Verifying manifest and checksum off-box...")
    manifest_path = LOCAL_BACKUP_DIR / "backup_manifest.json"
    if not manifest_path.exists():
        print("❌ Backup manifest missing on local host!")
        sys.exit(1)
        
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
        
    archive_file = LOCAL_BACKUP_DIR / manifest["archive_file"]
    if not archive_file.exists():
        print(f"❌ Backup archive '{manifest['archive_file']}' missing on local host!")
        sys.exit(1)
        
    actual_hash = compute_sha256(archive_file)
    expected_hash = manifest["checksum"]
    
    if actual_hash != expected_hash:
        print(f"❌ Checksum mismatch! Expected: {expected_hash}, Got: {actual_hash}")
        sys.exit(1)
        
    print(f"🟢 3-2-1 verification successful: Archive is stored off-site and checksum matches.")
    
    # 4. Perform tested restore
    print("\n[4] Performing tested restore of the ledger...")
    with tempfile.TemporaryDirectory() as tmpdir:
        # Extract archive
        tar_cmd = ["tar", "-xzf", str(archive_file), "-C", tmpdir]
        subprocess.run(tar_cmd, check=True)
        
        # Check swarm_ledger.db presence
        restored_db = Path(tmpdir) / "backend/swarm_ledger.db"
        if not restored_db.exists():
            print("❌ Restored backup is missing backend/swarm_ledger.db!")
            sys.exit(1)
            
        # Connect and query the restored DB to prove integrity
        try:
            conn = sqlite3.connect(str(restored_db))
            cursor = conn.cursor()
            cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            print(f"🟢 Successfully opened restored database. Table count: {table_count}")
            
            # Query some rules or heartbeats
            cursor.execute("SELECT count(*) FROM runtime_heartbeats")
            hb_count = cursor.fetchone()[0]
            print(f"🟢 Heartbeats count: {hb_count}")
            conn.close()
        except Exception as db_err:
            print(f"❌ Database integrity check failed: {db_err}")
            sys.exit(1)
            
    # 5. Write tested restore proof markdown
    proof_md_path = ROOT / "docs/evidence/runtime/tested-restore-proof.md"
    proof_md_path.parent.mkdir(parents=True, exist_ok=True)
    
    proof_content = f"""# tested-restore-proof.md
# 3-2-1 Disaster Recovery Tested Restore Proof

This document provides evidence of a successful 3-2-1 off-box backup and tested restore loop.

## Audit Summary
- **Primary Source (1)**: Live environment on remote VPS `HOCH-200` (`100.87.18.15`)
- **Off-box Storage Copy (2)**: Downloaded to local MacBook Pro (`/Users/michaelhoch/hoch_agent_swarm/data/backups/remote_vps/`)
- **Media Separation (3)**: Cloud VPS disk to Local MacBook SSD storage
- **Restoration Test Date**: {manifest['created_at']}
- **Archive Checksum**: `{manifest['checksum']}`
- **Database Table Count**: {table_count}
- **Verdict**: **DISASTER_RECOVERY_VERIFIED_GO**

## Verbatim Logs
```
Remote backup file: {manifest['archive_file']}
Checksum verification: MATCH
Restored DB query: SELECT count(*) FROM runtime_heartbeats -> Count = {hb_count}
```
"""
    proof_md_path.write_text(proof_content, encoding="utf-8")
    print(f"\n🟢 Tested restore proof saved to: {proof_md_path}")
    print("✅ 3-2-1 Backup & Restore test PASSED.")
    sys.exit(0)

if __name__ == "__main__":
    main()
