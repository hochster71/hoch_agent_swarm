#!/usr/bin/env python3
"""REQ-ES-001 — the council dispatched to >=2 real adapters with zero founder copy/paste."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
node = ROOT / "coordination" / "council" / "relay" / "H1D_pert_node.json"
if not node.exists():
    print("H1D relay node evidence absent"); sys.exit(1)
d = json.loads(node.read_text())
ok = (d.get("state") == "COMPLETED"
      and d.get("state_reason") == "MULTI_ADAPTER_VALIDATED_EVIDENCE"
      and len(d.get("accepted_adapters") or []) >= 2
      and d.get("manual_copy_paste_operations") == 0)
print(f"state={d.get('state')} adapters={d.get('accepted_adapters')} copypaste={d.get('manual_copy_paste_operations')}")
sys.exit(0 if ok else 1)
