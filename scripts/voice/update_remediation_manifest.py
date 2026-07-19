#!/usr/bin/env python3
import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def main():
    manifest_path = ROOT / "coordination/security/voice_remediation_manifest.json"
    if not manifest_path.exists():
        print(f"[-] Manifest file not found at: {manifest_path}")
        return

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    expected_changed_files = manifest.get("expected_changed_files", [])
    if not expected_changed_files and "expected_files" in manifest:
        expected_changed_files = list(manifest["expected_files"].keys())
        
    expected_files = {}

    for rel_path in expected_changed_files:
        abs_path = ROOT / rel_path
        if not abs_path.exists():
            print(f"[-] Warning: expected file {rel_path} does not exist in working tree")
            continue
        # compute hash
        file_bytes = abs_path.read_bytes()
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        expected_files[rel_path] = file_hash

    # update manifest structure
    manifest["expected_files"] = expected_files
    if "expected_changed_files" in manifest:
        del manifest["expected_changed_files"]

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"[+] Successfully updated manifest expected_files with {len(expected_files)} hashes.")

if __name__ == "__main__":
    main()
