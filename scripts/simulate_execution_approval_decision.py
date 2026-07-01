#!/usr/bin/env python3
# scripts/simulate_execution_approval_decision.py
# Simulates Michael Hoch's Founder / Owner approval decision on a queued proposal.

import os
import sys
import json
import datetime
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "has_live_project_tracker" / "data"

QUEUE_JSON = DATA_DIR / "hoch_execution_approval_queue.json"
DECISION_LOG_MD = PROJECT_ROOT / "docs/evidence/runtime/execution-approval-decision-log.md"

def print_usage():
    print("Usage: python3 scripts/simulate_execution_approval_decision.py <proposal_id> <decision>")
    print("Decisions: APPROVED | REJECTED | NEEDS_MORE_EVIDENCE")

def main():
    if len(sys.argv) < 3:
        print_usage()
        sys.exit(1)

    proposal_id = sys.argv[1]
    decision = sys.argv[2].upper()

    if decision not in ["APPROVED", "REJECTED", "NEEDS_MORE_EVIDENCE"]:
        print(f"Error: Invalid decision '{decision}'.")
        print_usage()
        sys.exit(1)

    if not os.path.exists(QUEUE_JSON):
        print(f"Error: Approval queue database does not exist at {QUEUE_JSON}")
        sys.exit(1)

    # Load approval queue
    with open(QUEUE_JSON, "r", encoding="utf-8") as f:
        queue = json.load(f)

    # Find proposal
    proposal = None
    for p in queue:
        if p["proposal_id"] == proposal_id:
            proposal = p
            break

    if not proposal:
        print(f"Error: Proposal ID '{proposal_id}' not found in the queue.")
        sys.exit(1)

    # Check safe write gate constraints: DESTRUCTIVE actions are denied by default under zero trust
    if proposal["action_type"] == "DESTRUCTIVE" and decision == "APPROVED":
        print(f"Zero-Trust Policy Block: Cannot approve DESTRUCTIVE action '{proposal_id}' without manual policy bypass.")
        sys.exit(1)

    # Update status
    old_status = proposal["approval_status"]
    proposal["approval_status"] = decision
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    proposal["last_verified_at"] = timestamp

    # Save update
    with open(QUEUE_JSON, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2)

    print(f"[SUCCESS] Updated proposal '{proposal_id}' status from '{old_status}' to '{decision}'")

    # Append to decision log evidence
    log_exists = os.path.exists(DECISION_LOG_MD)
    with open(DECISION_LOG_MD, "a", encoding="utf-8") as f:
        if not log_exists:
            f.write("# Swarm Execution Approval Decision Log\n\n")
            f.write("This log archives manual/simulated decisions made on execution proposals under zero-trust safety gates.\n\n")
            f.write("| Timestamp | Proposal ID | Action Title | Risk | Old Status | New Status | Signatory |\n")
            f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        f.write(f"| {timestamp} | `{proposal_id}` | {proposal['action_title']} | {proposal['risk_level']} | {old_status} | **{decision}** | Michael Hoch (Founder Sign-off) |\n")

    print(f"[PASS] Decision logged to: {DECISION_LOG_MD}")

if __name__ == "__main__":
    main()
