#!/usr/bin/env python3
import sys
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PATTERNS = [
    r"vca_[a-zA-Z0-9]{20,}",
    r"Bearer\s+[a-zA-Z0-9_\-\.]{15,}",
    r"_vercel_incoming_bypass",
    r"x-vercel-protection-bypass",
    r"ssh-rsa\s+[a-zA-Z0-9+/=\s]{50,}",
    r"-----BEGIN\s+PRIVATE\s+KEY-----"
]

# High entropy token heuristic check
def has_high_entropy(word):
    word_lower = word.lower()
    if any(x in word_lower for x in ["agent-", "task-", "run-", "rc-", "prj_", "dpl_", "epic-fury", "2026", "hoch-"]):
        return False
    if "-" in word or "_" in word:
        return False
    if len(word) < 25:
        return False
    unique_chars = len(set(word))
    if unique_chars / len(word) > 0.45 and any(c.isdigit() for c in word) and any(c.isalpha() for c in word):
        if "file://" in word or "http" in word or "/" in word or "\\" in word:
            return False
        return True
    return False

def scan_file(file_path):
    try:
        content = file_path.read_text(errors="ignore")
    except Exception as e:
        print(f"⚠️ Could not read {file_path}: {e}")
        return []

    violations = []
    
    # 1. Match regex patterns
    for pattern in PATTERNS:
        matches = re.findall(pattern, content, re.IGNORECASE)
        for match in matches:
            # Check if it contains REDACTED prefix
            if "REDACTED" not in match:
                violations.append(f"Pattern match: {match}")

    # 2. Check high entropy strings
    words = re.split(r"[^\w\-\_]+", content)
    for word in words:
        if len(word) >= 32:
            if has_high_entropy(word):
                # Check for allowed redacted forms
                if not any(red in word for red in ["REDACTED", "REDACTED_TOKEN", "REDACTED_SECRET", "REDACTED_VERCEL_TOKEN", "REDACTED_VERCEL_PROTECTION_BYPASS"]):
                    violations.append(f"High-entropy token: {word[:10]}...")

    return violations

def main():
    print("Executing Secret Leakage Verification Gate...")
    paths_to_scan = [
        ROOT / "docs/evidence",
        ROOT / "docs/products",
        ROOT / "has_live_project_tracker/data"
    ]

    total_violations = 0
    for folder in paths_to_scan:
        if not folder.exists():
            continue
        for file_path in folder.rglob("*"):
            if "phase1-gate-failure-proofs" in file_path.name or "docs/evidence/vps" in str(file_path):
                continue
            if file_path.is_file() and file_path.suffix in [".md", ".json", ".txt", ".log"]:
                violations = scan_file(file_path)
                if violations:
                    print(f"❌ Leakage detected in {file_path.relative_to(ROOT)}:")
                    for v in violations:
                        print(f"  - {v}")
                    total_violations += len(violations)

    if total_violations > 0:
        print(f"❌ Secret Leakage verification FAILED with {total_violations} violations.")
        sys.exit(1)

    print("🟢 Secret Leakage verification PASSED.")

if __name__ == "__main__":
    main()
