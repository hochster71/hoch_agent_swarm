#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def main():
    manifest_path = ROOT / "coordination/security/voice_remediation_manifest.json"
    if not manifest_path.exists():
        print(f"[-] Manifest file not found at: {manifest_path}")
        sys.exit(1)
        
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    expected_files = manifest.get("expected_files", {})
    governed_prefixes = manifest.get("governed_prefixes", [])
    
    missing_files = []
    unexpected_files = []
    hash_mismatches = []
    
    # 1. Get current commit HEAD
    try:
        current_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(ROOT)).decode().strip()
    except Exception as e:
        print(f"[-] Failed to get HEAD commit SHA: {e}")
        sys.exit(1)
        
    # 2. Verify expected files exist and match hashes
    for rel_path, expected_hash in expected_files.items():
        abs_path = ROOT / rel_path
        if not abs_path.exists():
            missing_files.append(rel_path)
            continue
            
        # compute actual hash
        file_bytes = abs_path.read_bytes()
        actual_hash = hashlib.sha256(file_bytes).hexdigest()
        if actual_hash != expected_hash:
            hash_mismatches.append({
                "file": rel_path,
                "expected": expected_hash,
                "actual": actual_hash
            })
            
    # 3. Check git status to ensure working tree for governed paths is clean
    try:
        status_lines = subprocess.check_output(["git", "status", "--porcelain"], cwd=str(ROOT)).decode().splitlines()
        clean_governed = True
        for line in status_lines:
            parts = line.strip().split(None, 1)
            if len(parts) == 2:
                status_flag, file_path = parts
                for prefix in governed_prefixes:
                    if file_path.startswith(prefix):
                        clean_governed = False
                        unexpected_files.append(file_path)
                        break
    except Exception as e:
        print(f"[-] Failed to get git status: {e}")
        sys.exit(1)

    verification = {
        "verification_mode": "HEAD_TREE",
        "verified_head_sha": current_sha,
        "expected_files": len(expected_files),
        "missing_files": missing_files,
        "unexpected_files": unexpected_files,
        "hash_mismatches": hash_mismatches,
        "tree_verified": len(missing_files) == 0 and len(unexpected_files) == 0 and len(hash_mismatches) == 0
    }
    
    # Write verification results to evidence file
    evidence_dir = ROOT / "coordination/evidence/voice_remediation_manifest_verification"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    with open(evidence_dir / "tree_verification_results.json", "w", encoding="utf-8") as out_f:
        json.dump(verification, out_f, indent=2)
        
    print(json.dumps(verification, indent=2))
    
    if verification["tree_verified"]:
        print("[+] Head tree verification passed [PASS]")
        sys.exit(0)
    else:
        print("[-] Head tree verification failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
