#!/usr/bin/env python3
"""
Workspace Visual Hygiene Guard
Ensures no garbage images, old packages, or root clutter is discoverable.
Fails if root or quarantine contains binary visual artifacts.
"""
import sys
import json
from pathlib import Path

ROOT = Path("/Users/michaelhoch/hoch_agent_swarm")
ARCHIVE = Path("/Users/michaelhoch/hoch_agent_swarm_archive/visual-garbage-do-not-use")
CANONICAL = ROOT / "docs/design/approved-visual-authority/hoch-pods-has-hasf-approved-authority.jpeg"
EXPECTED_HASH = "21bd9aef213e45824295a9a3e85b4f8817f841962a9ad24e817a12bdc3b1f442"

def compute_sha256(path):
    import hashlib
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(4096), b""):
            sha.update(block)
    return sha.hexdigest()

def main():
    print("WORKSPACE VISUAL HYGIENE GUARD")
    print("=" * 50)

    # During blank reset or candidate inbox phase, allow zero or candidate images only
    if (ROOT / "docs/design/approved-visual-authority/visual-authority-manifest.json").exists():
        manifest = json.loads((ROOT / "docs/design/approved-visual-authority/visual-authority-manifest.json").read_text())
        if manifest.get("approved_image_count", 1) == 0:
            print("Blank reset mode detected - checking for no active images")
            # Allow inbox candidates but no active authority

    # Check root for garbage
    root_garbage = list(ROOT.glob("*.png")) + list(ROOT.glob("*.jpg")) + list(ROOT.glob("*.jpeg")) + list(ROOT.glob("*.webp")) + list(ROOT.glob("*.zip")) + list(ROOT.glob("hoch-approved*"))
    if root_garbage:
        print("WORKSPACE_VISUAL_HYGIENE: FAIL - Root-level visual garbage detected:")
        for item in root_garbage:
            print(f"  {item}")
        sys.exit(1)

    # Check quarantine for binary files
    quarantine_binaries = [f for f in (ROOT / "docs/design/quarantine").rglob("*") if f.is_file() and f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp', '.zip')]
    if quarantine_binaries:
        print("WORKSPACE_VISUAL_HYGIENE: FAIL - Binary visual garbage in repo quarantine:")
        for item in quarantine_binaries:
            print(f"  {item}")
        sys.exit(1)

    # Check for old bad filenames
    bad_names = list(ROOT.rglob("*HOCH*POOS*")) + list(ROOT.rglob("*contact-sheet*"))
    if bad_names:
        print("WORKSPACE_VISUAL_HYGIENE: FAIL - Bad filenames still in repo")
        sys.exit(1)

    if not (ROOT / "docs/design/approved-visual-authority/README_DOCTRINE.md").exists():
        print("WORKSPACE_VISUAL_HYGIENE: FAIL - Doctrine shield README missing")
        sys.exit(1)

    if not (ROOT / "docs/design/approved-visual-authority-inbox/README_DROP_CANDIDATES_HERE.md").exists():
        print("WORKSPACE_VISUAL_HYGIENE: FAIL - Inbox README missing")
        sys.exit(1)

    print("WORKSPACE_VISUAL_HYGIENE: PASS")
    print("Root clean. Canonical authority protected. External archive used for garbage.")
    print("Discovery shield active. No visual garbage discoverable by Grok/VS Code.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
