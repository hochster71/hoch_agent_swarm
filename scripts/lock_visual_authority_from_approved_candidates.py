#!/usr/bin/env python3
"""
Visual Authority Doctrine Lock Script
Fails closed unless Michael explicitly approves with the phrase.

Approval phrase must be in a file: docs/design/approved-visual-authority-inbox/MICHAEL_APPROVAL.txt or provided via environment.

This script refuses to lock doctrine without explicit Michael approval.
"""
import sys
from pathlib import Path

ROOT = Path("/Users/michaelhoch/hoch_agent_swarm")
APPROVAL_FILE = ROOT / "docs/design/approved-visual-authority-inbox/MICHAEL_APPROVAL.txt"
REQUIRED_PHRASE = "APPROVE IMAGE DOCTRINE LOCK"

def main():
    print("VISUAL AUTHORITY DOCTRINE LOCK")
    print("=" * 50)

    if not APPROVAL_FILE.exists():
        print("VISUAL_AUTHORITY_LOCK: BLOCKED_AWAITING_MICHAEL_APPROVAL")
        print(f"Create {APPROVAL_FILE} containing exactly: '{REQUIRED_PHRASE}'")
        print("Or reply with the phrase to trigger lock.")
        sys.exit(1)

    approval_text = APPROVAL_FILE.read_text().strip()
    if REQUIRED_PHRASE not in approval_text:
        print("VISUAL_AUTHORITY_LOCK: BLOCKED_AWAITING_MICHAEL_APPROVAL")
        print(f"Approval file must contain exactly: '{REQUIRED_PHRASE}'")
        sys.exit(1)

    print("Michael approval detected.")
    print("Running doctrine lock from candidates...")
    # Future implementation would move candidates, update manifest, etc.
    # For now, this is placeholder that confirms approval but does not lock until further phases.
    print("VISUAL_AUTHORITY_LOCK: APPROVED — Proceeding to lock in next phase.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
