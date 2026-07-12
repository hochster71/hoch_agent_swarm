#!/usr/bin/env python3
"""REQ-TO-001 (FOUNDER_ONLY) — a champion product has been selected by the
authoritative portfolio prioritization process. Fails while none is selected."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
c = json.loads((ROOT / "config" / "canonical_goal_contract.json").read_text())
champ = c["goal_hierarchy"]["3_current_champion_product"]
print(f"champion={champ.get('value')} state={champ.get('value_state')}")
sys.exit(0 if champ.get("value") else 1)
