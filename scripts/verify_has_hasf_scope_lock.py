#!/usr/bin/env python3
"""
HAS/HASF Scope Lock Drift Guard
Enforces executive automation scope lock.
Fails if drift detected.
"""
import json
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path("/Users/michaelhoch/hoch_agent_swarm")
SCOPE_LOCK = ROOT / "has_live_project_tracker/data/has_hasf_scope_lock.json"
OPERATOR_QUEUE = ROOT / "has_live_project_tracker/data/operator_next_actions.json"

def main():
    print("HAS/HASF SCOPE LOCK DRIFT GUARD")
    print("=" * 60)
    print(f"Generated at: {datetime.now().isoformat()}")

    if not SCOPE_LOCK.exists():
        print("HAS_HASF_SCOPE_LOCK: FAIL - Scope lock JSON missing")
        sys.exit(1)

    lock = json.loads(SCOPE_LOCK.read_text())
    if lock.get("doctrine_id") != "HAS_HASF_EXECUTIVE_AUTOMATION_SCOPE_LOCK_v1":
        print("HAS_HASF_SCOPE_LOCK: FAIL - Wrong doctrine ID")
        sys.exit(1)

    if lock.get("michael_role") != "EXECUTIVE_APPROVER_ONLY":
        print("HAS_HASF_SCOPE_LOCK: FAIL - Michael role not EXECUTIVE_APPROVER_ONLY")
        sys.exit(1)

    if not OPERATOR_QUEUE.exists():
        print("HAS_HASF_SCOPE_LOCK: FAIL - Operator queue missing")
        sys.exit(1)

    queue = json.loads(OPERATOR_QUEUE.read_text())
    actions = queue.get("queue", [])
    if len(actions) > 1:
        print("HAS_HASF_SCOPE_LOCK: FAIL - Multiple next actions emitted (violates one-next-action policy)")
        sys.exit(1)

    print("HAS_HASF_SCOPE_LOCK: PASS")
    print("Drift guard active. Michael is executive approver only.")
    print(f"Current priority: {lock.get('current_priority', 'Prove local runner automation')}")
    print(f"Single next action: {len(actions)} (enforced)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
