#!/usr/bin/env python3
import hashlib
import json
import os
import sys

def verify():
    dir_path = os.path.dirname(os.path.abspath(__file__))
    manifest_path = os.path.join(dir_path, "manifest.json")
    
    if not os.path.exists(manifest_path):
        print(f"Error: manifest.json not found in {dir_path}", file=sys.stderr)
        return 1

    try:
        with open(manifest_path, "r") as fd:
            manifest = json.load(fd)
    except Exception as e:
        print(f"Error reading manifest: {e}", file=sys.stderr)
        return 1

    artifacts = manifest.get("artifacts", [])
    if not artifacts:
        print("Error: No artifacts found in manifest.json", file=sys.stderr)
        return 1

    mismatches = 0
    print("Checking HELM Autoloop Restart Audit Artifact Integrity...")
    for art in artifacts:
        name = art.get("name")
        expected_hash = art.get("sha256")
        
        art_path = os.path.join(dir_path, name)
        if not os.path.exists(art_path):
            print(f"  ✗ {name}: FILE MISSING")
            mismatches += 1
            continue

        try:
            with open(art_path, "rb") as fd:
                actual_hash = hashlib.sha256(fd.read()).hexdigest()
        except Exception as e:
            print(f"  ✗ {name}: UNABLE TO READ ({e})")
            mismatches += 1
            continue

        if actual_hash == expected_hash:
            print(f"  ✓ {name}: PASS")
        else:
            print(f"  ✗ {name}: HASH MISMATCH")
            print(f"    Expected: {expected_hash}")
            print(f"    Actual:   {actual_hash}")
            mismatches += 1

    if mismatches > 0:
        print(f"\nVerification FAILED: {mismatches} mismatch(es) detected.", file=sys.stderr)
        return 1
    else:
        print("\nVerification SUCCESS: All audit artifacts have valid integrity.")
        return 0

if __name__ == "__main__":
    sys.exit(verify())
