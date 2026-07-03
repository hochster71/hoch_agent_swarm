#!/usr/bin/env python3
import json
import sys
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_FILE = ROOT / "has_live_project_tracker/data/evidence_manifest.json"

def get_sha256(file_path):
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def compute_entry_hash(entry):
    # Strip hash key to recalculate
    e_copy = entry.copy()
    if "entry_hash" in e_copy:
        del e_copy["entry_hash"]
    serialized = json.dumps(e_copy, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

def verify_manifest():
    print("Executing Evidence Integrity Verification Gate...")
    
    if not MANIFEST_FILE.exists():
        print("❌ Verification failed: evidence_manifest.json is missing.")
        sys.exit(1)
        
    with open(MANIFEST_FILE, "r") as f:
        try:
            manifest = json.load(f)
        except Exception as e:
            print(f"❌ Verification failed: Failed to parse evidence manifest: {e}")
            sys.exit(1)
            
    seen_ids = set()
    prev_hash = "0"
    
    for idx, entry in enumerate(manifest):
        entry_id = entry.get("entry_id")
        rel_path = entry.get("evidence_path")
        sha256 = entry.get("evidence_sha256")
        recorded_prev_hash = entry.get("previous_entry_hash")
        recorded_entry_hash = entry.get("entry_hash")
        
        # 1. Check duplicate IDs
        if entry_id in seen_ids:
            print(f"❌ Verification failed: Duplicate entry ID detected: {entry_id}")
            sys.exit(1)
        seen_ids.add(entry_id)
        
        # 2. Check file existence
        file_path = ROOT / rel_path
        if not file_path.exists():
            print(f"❌ Verification failed: Evidence file listed in manifest does not exist: {rel_path}")
            sys.exit(1)
            
        # 3. Check hash mismatch
        actual_sha256 = get_sha256(file_path)
        if actual_sha256 != sha256:
            print(f"❌ Verification failed: Hash mismatch for evidence file: {rel_path}. Recorded: {sha256}, Actual: {actual_sha256}")
            sys.exit(1)
            
        # 4. Check entry hash validity
        recomputed_entry_hash = compute_entry_hash(entry)
        if recomputed_entry_hash != recorded_entry_hash:
            print(f"❌ Verification failed: Invalid entry hash for {entry_id}. Recomputed: {recomputed_entry_hash}, Recorded: {recorded_entry_hash}")
            sys.exit(1)
            
        # 5. Check previous entry hash matching
        if recorded_prev_hash != prev_hash:
            print(f"❌ Verification failed: Chain break at {entry_id}. Previous entry hash does not match. Expected: {prev_hash}, Recorded: {recorded_prev_hash}")
            sys.exit(1)
            
        prev_hash = recorded_entry_hash
        
    print("🟢 Evidence integrity verification PASSED.")
    return True

if __name__ == "__main__":
    verify_manifest()
