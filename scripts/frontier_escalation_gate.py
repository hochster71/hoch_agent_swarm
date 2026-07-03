#!/usr/bin/env python3
"""
Frontier Escalation Gate
Uses cost governor and routing policy to decide when to escalate to Grok or other frontier models.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

DATA = Path("has_live_project_tracker/data")
DATA.mkdir(parents=True, exist_ok=True)
ESCALATION_QUEUE = DATA / "frontier_escalation_queue.json"

def main():
    print("FRONTIER ESCALATION GATE")
    print("=" * 50)
    print(f"Generated at: {datetime.now().isoformat()}")

    try:
        cost = json.loads((DATA / "cost_governor.json").read_text())
        routing = json.loads((DATA / "model_routing_policy.json").read_text())
    except:
        print("FRONTIER_ESCALATION_GATE: FAIL - Missing governor or routing data")
        sys.exit(1)

    if cost["grok"]["credits_remaining_usd"] < 25:
        print("Grok credits low. Blocking non-critical frontier use.")
        escalation = {"status": "BLOCKED_LOW_CREDITS", "recommended": "NONE"}
    else:
        escalation = {
            "status": "LOCAL_FIRST",
            "recommended": "NONE",
            "message": "All routine work routed to local AI. Frontier escalation only for scoped complex patches with approval."
        }

    ESCALATION_QUEUE.write_text(json.dumps(escalation, indent=2))
    print(json.dumps(escalation, indent=2))
    print("FRONTIER_ESCALATION_GATE: PASS")
    return 0

if __name__ == "__main__":
    sys.exit(main())
