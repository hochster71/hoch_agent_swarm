#!/usr/bin/env python3
import json
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
    e_copy = entry.copy()
    if "entry_hash" in e_copy:
        del e_copy["entry_hash"]
    serialized = json.dumps(e_copy, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

def recalculate():
    print("Recalculating all manifest hashes...")
    if not MANIFEST_FILE.exists():
        return
        
    with open(MANIFEST_FILE, "r") as f:
        manifest = json.load(f)
        
    prev_hash = "0"
    for entry in manifest:
        rel_path = entry["evidence_path"]
        file_path = ROOT / rel_path
        if file_path.exists():
            entry["evidence_sha256"] = get_sha256(file_path)
        entry["previous_entry_hash"] = prev_hash
        entry["entry_hash"] = compute_entry_hash(entry)
        prev_hash = entry["entry_hash"]
        
    with open(MANIFEST_FILE, "w") as f:
        json.dump(manifest, f, indent=2)
    print("🟢 All manifest entry hashes recalculated and chained.")

if __name__ == "__main__":
    recalculate()
