#!/usr/bin/env python3
"""REQ-TO-003 — full autonomous path intake -> DOORSTEP proven end to end."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "coordination" / "goal" / "intake_to_doorstep.json"
relay = ROOT / "coordination" / "council" / "relay" / "H1D_pert_node.json"
stages = {
    "dispatch_relay": relay.exists(),
    "intake": False, "plan": False, "execute": False,
    "validate": relay.exists(), "evidence": relay.exists(), "doorstep": False,
}
ok = all(stages.values())
report = {"requirement": "REQ-TO-003", "stages": stages,
          "status": "PASS" if ok else "FAIL",
          "reason": None if ok else "Only the dispatch->validate->evidence segment is proven (H1D). Intake, plan, execute, and DOORSTEP handoff are not yet wired end to end."}
OUT.parent.mkdir(parents=True, exist_ok=True); OUT.write_text(json.dumps(report, indent=2) + "\n")
print(f"stages proven: {sum(stages.values())}/{len(stages)}")
sys.exit(0 if ok else 1)
