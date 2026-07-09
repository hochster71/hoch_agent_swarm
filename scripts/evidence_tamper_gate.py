#!/usr/bin/env python3
# =============================================================================
# evidence_tamper_gate.py
# Verifies the SHA256 hashes of all compiled evidence logs against manifest.
# =============================================================================
import os
import sys
import json
import hashlib

def get_latest_run_id():
    try:
        with open("data/runtime_scenarios/latest_run_id", "r") as f:
            return f.read().strip()
    except Exception:
        return "latest"

def compute_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()

def verify():
    run_id = get_latest_run_id()
    manifest_path = f"docs/evidence/runtime_scenarios/{run_id}/evidence_manifest.json"
    
    print(f"==> Verifying evidence integrity via manifest: {manifest_path}...")
    
    if not os.path.exists(manifest_path):
        print("❌ FAIL: Evidence manifest file is missing.")
        sys.exit(1)
        
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
        
    mismatches = 0
    for item in manifest.get("artifacts", []):
        path = item.get("path")
        expected_hash = item.get("sha256")
        
        if not os.path.exists(path):
            print(f"❌ FAIL: Evidence artifact '{path}' is missing.")
            mismatches += 1
            continue
            
        actual_hash = compute_sha256(path)
        if actual_hash != expected_hash:
            print(f"❌ FAIL: Hash mismatch for '{path}' (Expected: {expected_hash}, got: {actual_hash})")
            mismatches += 1
            
    if mismatches > 0:
        print(f"❌ FAIL: Detected {mismatches} evidence hash mismatches.")
        sys.exit(1)
        
    # C3: hash equality alone is forgeable (rewrite artifact + rewrite manifest).
    # If the manifest carries a MAC, require it to verify against the founder
    # key AND appear in the external append-only anchor. When no MAC is present
    # (legacy manifests), we stay backward-compatible but warn loudly.
    if manifest.get("manifest_mac"):
        try:
            sys.path.insert(0, os.getcwd())
            from backend.mission_control.evidence_integrity import verify_manifest
            res = verify_manifest(manifest)
            if not res["ok"]:
                print(f"❌ FAIL: Evidence MAC/anchor check failed: {res['reason']} "
                      f"(first_bad={res.get('first_bad')})")
                sys.exit(1)
            print("✅ Evidence MAC verified and present in external anchor.")
        except FileNotFoundError as ex:
            print(f"❌ FAIL: {ex}")
            sys.exit(1)
    else:
        print("⚠️  WARN: manifest has no MAC (legacy). Hash-only integrity — "
              "rebuild with evidence_integrity.build_manifest to make it tamper-evident.")

    print("✅ Evidence Integrity Gate Passed: All artifact hashes validated successfully.")
    sys.exit(0)

if __name__ == "__main__":
    verify()
