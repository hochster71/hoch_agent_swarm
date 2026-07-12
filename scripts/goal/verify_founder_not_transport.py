#!/usr/bin/env python3
"""REQ-NS-001 — the founder is not the routine transport layer.

Measured from the dispatch ledger: every council task must show zero manual
copy/paste operations. No ledger => UNKNOWN => zero contribution.
"""
import glob, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
files = sorted(glob.glob(str(ROOT / "coordination" / "council" / "relay" / "*.council.json")))
if not files:
    print("no council task evidence"); sys.exit(1)
bad = 0
for f in files:
    d = json.loads(Path(f).read_text())
    if d.get("manual_copy_paste_operations", 1) != 0:
        bad += 1
print(f"council tasks: {len(files)} | tasks requiring founder transport: {bad}")
sys.exit(0 if bad == 0 else 1)
