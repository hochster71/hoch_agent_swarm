#!/usr/bin/env python3
"""REQ-NS-002 — verified_founder_minutes_per_shipped_dollar is MEASURED, not estimated.

It needs a real founder-minutes ledger AND real shipped revenue. Neither exists.
Emitting a number here would be a fabrication, so this fails honestly.
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
ledger = ROOT / "coordination" / "goal" / "founder_minutes_ledger.jsonl"
print(f"founder_minutes_ledger present: {ledger.exists()} | shipped revenue: $0")
sys.exit(1)
