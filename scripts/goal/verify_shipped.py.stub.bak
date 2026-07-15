#!/usr/bin/env python3
"""REQ-TO-002 (FOUNDER_ONLY) — champion product shipped to production distribution."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "coordination" / "goal" / "shipped_report.json"
report = {"requirement": "REQ-TO-002", "shipped": False,
          "reason": "No champion selected; no release or rollback package signed or submitted.",
          "status": "FAIL"}
OUT.parent.mkdir(parents=True, exist_ok=True); OUT.write_text(json.dumps(report, indent=2) + "\n")
print("shipped=False (no champion, nothing submitted)")
sys.exit(1)
