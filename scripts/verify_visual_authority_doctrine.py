#!/usr/bin/env python3
"""
HAS/HASF Visual Authority Doctrine Guard
Enforces single approved image ONLY. No HOCH POOS, no multi-image doctrines, no variance.
"""
import hashlib
import json
import sys
from pathlib import Path

def compute_sha256(file_path: Path) -> str:
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def main():
    root = Path("/Users/michaelhoch/hoch_agent_swarm")
    manifest_path = root / "docs/design/approved-visual-authority/visual-authority-manifest.json"
    canonical_image = root / "docs/design/approved-visual-authority/hoch-pods-has-hasf-approved-authority.jpeg"
    expected_hash = "21bd9aef213e45824295a9a3e85b4f8817f841962a9ad24e817a12bdc3b1f442"

    print("HAS/HASF VISUAL AUTHORITY DOCTRINE GUARD")
    print("=" * 60)

    if not manifest_path.exists():
        print("VISUAL_AUTHORITY_DOCTRINE: FAIL - Manifest missing")
        sys.exit(1)

    manifest = json.loads(manifest_path.read_text())
    if manifest.get("doctrine") == "BLANK_IMAGE_RESET_PENDING_MICHAEL_REPOPULATION" or manifest.get("approved_image_count") == 0:
        print("VISUAL_AUTHORITY_DOCTRINE: PASS - Blank reset mode accepted")
        print("Image authority active: false")
        return 0

    if manifest.get("approved_image_count") != 1 or manifest.get("no_variance") is not True:
        print("VISUAL_AUTHORITY_DOCTRINE: FAIL - Not single-image no-variance doctrine")
        sys.exit(1)

    if not canonical_image.exists():
        print("VISUAL_AUTHORITY_DOCTRINE: FAIL - Canonical image missing")
        sys.exit(1)

    actual_hash = compute_sha256(canonical_image)
    if actual_hash != expected_hash:
        print(f"VISUAL_AUTHORITY_DOCTRINE: FAIL - Hash mismatch. Got {actual_hash}")
        sys.exit(1)

    # Check for forbidden HOCH POOS or old doctrines
    forbidden_patterns = ["HOCH POOS", "© HOCH POOS", "two-image", "four-image", "multi-image"]
    for pattern in forbidden_patterns:
        if any(pattern.lower() in str(p).lower() for p in root.glob("**/*") if not "quarantine" in str(p)):
            print(f"VISUAL_AUTHORITY_DOCTRINE: FAIL - Forbidden reference to '{pattern}' found")
            sys.exit(1)

    print("VISUAL_AUTHORITY_DOCTRINE: PASS")
    print(f"Single approved image verified: {canonical_image.name}")
    print(f"SHA256: {actual_hash}")
    print("Doctrine: LOCKED - Only this image is authority. No variance allowed.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
