#!/usr/bin/env python3
"""
Visual Authority Candidate Review Script
Reads only from approved-visual-authority-inbox/
Creates review files
Marks as CANDIDATE_ONLY_NOT_AUTHORITY
Refuses to approve or lock doctrine
"""
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from PIL import Image  # optional for dimensions; fallback if not installed

ROOT = Path("/Users/michaelhoch/hoch_agent_swarm")
INBOX = ROOT / "docs/design/approved-visual-authority-inbox"
REVIEW_MD = ROOT / "docs/evidence/ui/visual-authority-candidate-review.md"
REVIEW_HTML = ROOT / "docs/evidence/ui/visual-authority-candidate-review.html"

def compute_sha256(path):
    sha256_hash = hashlib.sha256()
    with open(path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def get_dimensions(path):
    try:
        with Image.open(path) as img:
            return f"{img.width}x{img.height}"
    except:
        return "UNKNOWN"

def main():
    print("VISUAL AUTHORITY CANDIDATE REVIEW")
    print("=" * 50)
    print(f"Generated at: {datetime.now().isoformat()}")
    print("Inbox: docs/design/approved-visual-authority-inbox/")

    images = [f for f in INBOX.glob("*") if f.is_file() and f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg')]
    if not images:
        print("VISUAL_AUTHORITY_CANDIDATE_REVIEW: NO_CANDIDATES")
        print("No candidate images in inbox. Awaiting Michael upload.")
        return 0

    md_content = "# Visual Authority Candidate Review\n\n**Status**: CANDIDATE_ONLY_NOT_AUTHORITY\n**Doctrine**: BLANK_IMAGE_RESET_PENDING_MICHAEL_REPOPULATION\n\n"
    html_content = """<!DOCTYPE html>
<html>
<head><title>Visual Authority Candidate Review</title>
<style>body {font-family: system-ui; margin: 40px;} .candidate {border: 3px solid #0d6efd; padding: 20px; margin: 20px 0;}</style>
</head>
<body>
<h1>Visual Authority Candidate Review — CANDIDATE ONLY NOT AUTHORITY</h1>
<p><strong>Doctrine</strong>: BLANK_IMAGE_RESET_PENDING_MICHAEL_REPOPULATION | <strong>Approved Count</strong>: 0</p>
"""

    for img in images:
        sha = compute_sha256(img)
        dims = get_dimensions(img)
        md_content += f"## Candidate: {img.name}\n- Path: {img}\n- Dimensions: {dims}\n- SHA256: {sha}\n- Status: CANDIDATE_ONLY_NOT_AUTHORITY\n\n![Candidate](../approved-visual-authority-inbox/{img.name})\n\n---\n\n"
        html_content += f'<div class="candidate"><h2>{img.name}</h2><img src="../../approved-visual-authority-inbox/{img.name}" style="max-width:800px;"><p><strong>Path</strong>: {img}<br><strong>Dimensions</strong>: {dims}<br><strong>SHA256</strong>: {sha}<br><strong>Status</strong>: CANDIDATE_ONLY_NOT_AUTHORITY</p></div>\n'

    md_content += "\n**Michael must explicitly approve with 'APPROVE IMAGE DOCTRINE LOCK' before Grok can lock doctrine or move images.**\n"
    html_content += "<p><strong>Michael must explicitly approve with 'APPROVE IMAGE DOCTRINE LOCK' before Grok can lock doctrine or move images.</strong></p></body></html>"

    REVIEW_MD.write_text(md_content)
    REVIEW_HTML.write_text(html_content)

    print(f"Review files created: {REVIEW_MD} and {REVIEW_HTML}")
    print("VISUAL_AUTHORITY_CANDIDATE_REVIEW: PASS")
    print("Candidates marked CANDIDATE_ONLY_NOT_AUTHORITY. No doctrine lock performed.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
