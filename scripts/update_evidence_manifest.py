#!/usr/bin/env python3
import json
import sys
import hashlib
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = ROOT / "docs/evidence"
MANIFEST_FILE = ROOT / "has_live_project_tracker/data/evidence_manifest.json"

def get_sha256(file_path):
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def compute_entry_hash(entry):
    # Canonical JSON serialization
    serialized = json.dumps(entry, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

def update_manifest():
    print("Updating Evidence Manifest...")
    
    manifest = []
    if MANIFEST_FILE.exists() and MANIFEST_FILE.stat().st_size > 0:
        with open(MANIFEST_FILE, "r") as f:
            try:
                manifest = json.load(f)
            except:
                pass
                
    # Track existing paths
    existing_paths = {entry["evidence_path"]: entry for entry in manifest}
    
    # Discover files
    evidence_files = []
    for path in EVIDENCE_DIR.rglob("*"):
        if path.is_file() and path.suffix in [".md", ".json", ".txt"]:
            evidence_files.append(path)
            
    # Sort files by creation/modified time or alphabetically to keep deterministic order
    evidence_files.sort(key=lambda p: (p.stat().st_mtime, str(p)))
    
    updated = False
    
    for file_path in evidence_files:
        rel_path = str(file_path.relative_to(ROOT))
        sha256 = get_sha256(file_path)
        
        if rel_path in existing_paths:
            # Check if hash changed
            existing_entry = existing_paths[rel_path]
            if existing_entry["evidence_sha256"] != sha256:
                print(f"⚠️ Warning: Hash mismatch for existing file: {rel_path}. Run in repair mode to update.")
            continue
            
        # Create new entry
        prev_hash = "0"
        if manifest:
            prev_hash = manifest[-1]["entry_hash"]
            
        entry_id = f"entry-{len(manifest) + 1:04d}"
        
        entry = {
            "entry_id": entry_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "run_id": "20260702T222129Z-24-7-autonomy-reset",
            "task_id": "task-unspecified",
            "agent_id": "has_system",
            "model_backend": "none",
            "adapter_id": "none",
            "incident_class": "none",
            "evidence_path": rel_path,
            "evidence_sha256": sha256,
            "previous_entry_hash": prev_hash,
            "signature_status": "unsigned",
            "founder_approval_required": False,
            "created_by": "HELM_manifest_daemon"
        }
        
        # Calculate entry hash
        entry["entry_hash"] = compute_entry_hash(entry)
        manifest.append(entry)
        existing_paths[rel_path] = entry
        updated = True
        print(f"Added manifest entry {entry_id} for {rel_path}")
        
    if updated:
        MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(MANIFEST_FILE, "w") as f:
            json.dump(manifest, f, indent=2)
        print("🟢 Evidence manifest updated successfully.")
    else:
        print("🟢 Evidence manifest is already up to date.")

if __name__ == "__main__":
    update_manifest()
