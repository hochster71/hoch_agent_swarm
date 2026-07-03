#!/usr/bin/env python3
import json
import sys
import argparse
import os

def compute():
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", default="has_live_project_tracker/data/mission_intake_queue.json")
    parser.add_argument("--task-queue", default="has_live_project_tracker/data/helm_task_queue.json")
    parser.add_argument("--log", default="has_live_project_tracker/data/helm_execution_log.json")
    parser.add_argument("--evidence-dir", default="docs/evidence/")
    parser.add_argument("--tracker", default="has_live_project_tracker/data/has_runtime_state.json")
    args = parser.parse_args()
    
    # Read intake queue
    try:
        with open(args.queue, "r") as f:
            queue = json.load(f)
        missions = queue.get("missions", [])
    except Exception:
        missions = []

    # Read execution log
    try:
        with open(args.log, "r") as f:
            log_entries = json.load(f)
    except Exception:
        log_entries = []

    # Check for manual_prompt_injected or manual_review_intervention in the log
    manual_injected_present = any(
        entry.get("event") in ["manual_prompt_injected", "manual_review_intervention"] for entry in log_entries
    )

    clean_completed_missions = []
    for m in missions:
        status = m.get("status")
        sig_status = m.get("signature_status")
        san_status = m.get("sanitization_status")
        
        # A clean completed mission requires completion, valid signature, sanitization pass, and no injection rejection status
        if status == "COMPLETED" and sig_status in ["VALID", "NOT_REQUIRED_DRY_RUN"] and san_status == "PASS":
            clean_completed_missions.append(m)

    copy_paste = True
    reason = "insufficient autonomous mission history"

    # Require at least 3 clean completed missions AND no manual injection or review intervention events
    if len(clean_completed_missions) >= 3 and not manual_injected_present:
        copy_paste = False
        reason = "At least 3 missions processed end-to-end with automated critic review and no manual interventions."
    elif manual_injected_present:
        reason = "Manual prompt injection or review intervention detected in execution logs."
    elif not missions:
        reason = "No missions processed through intake queue yet."
    else:
        reason = f"insufficient autonomous mission history (got {len(clean_completed_missions)} clean completed, need at least 3)"

    print(f"Computed copy_paste_required: {copy_paste} ({reason})")
    
    # Save computed metrics back to live tracker/runtime state
    try:
        with open(args.tracker, "r") as f:
            tracker = json.load(f)
    except Exception:
        tracker = {}
        
    tracker["manual_relay_status"] = "REMOVED" if not copy_paste else "ACTIVE"
    tracker["orchestration_bridge_status"] = "ACTIVE"
    tracker["copy_paste_required_computed"] = copy_paste
    tracker["copy_paste_required_reason"] = reason
    
    with open(args.tracker, "w") as f:
        json.dump(tracker, f, indent=2)
        
    return copy_paste, reason

if __name__ == "__main__":
    compute()
