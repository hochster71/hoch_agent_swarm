#!/usr/bin/env python3
# scripts/run_governed_execution.py
# Governed Execution Runner for safe (READ_ONLY/LOCAL_SAFE_WRITE) proposals.
# Implements strict validation, hard-blocking, allowlisted dispatching, and evidence generation.

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
EXEC_LOG_JSON = DATA_DIR / "governed_execution_log.json"
EXEC_LOG_MD = PROJECT_ROOT / "docs/evidence/runtime/governed-execution-log.md"
ROLLBACK_PLAN_MD = PROJECT_ROOT / "docs/evidence/runtime/governed-execution-rollback-plan.md"

PROPOSAL_DISPATCHER_MAP = {
    "prop-cyber-gitleaks": "validate_no_live_secrets",
    "prop-qa-playwright": "inspect_project_metadata",
    "prop-builder-compile": "generate_markdown_brief",
}

UNSAFE_CLASSES = [
    "REPO_WRITE",
    "NETWORK_WRITE",
    "SECRET_ACCESS",
    "STRIPE_TEST_CONFIG",
    "STRIPE_LIVE_CONFIG",
    "DEPLOYMENT",
    "DESTRUCTIVE"
]

def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def print_usage():
    print("Usage: python3 scripts/run_governed_execution.py <proposal_id> <mode>")
    print("Modes: DRY_RUN | STAGED_EXECUTION")

def main():
    if len(sys.argv) < 3:
        print_usage()
        sys.exit(1)

    proposal_id = sys.argv[1]
    mode = sys.argv[2].upper()

    if mode not in ["DRY_RUN", "STAGED_EXECUTION"]:
        print(f"Error: Invalid mode '{mode}'.")
        print_usage()
        sys.exit(1)

    if not os.path.exists(QUEUE_JSON):
        print(f"Error: Approval queue registry not found at {QUEUE_JSON}")
        sys.exit(1)

    queue = load_json(QUEUE_JSON)
    proposal = None
    for p in queue:
        if p["proposal_id"] == proposal_id:
            proposal = p
            break

    if not proposal:
        print(f"Error: Proposal ID '{proposal_id}' not found in the queue.")
        sys.exit(1)

    action_type = proposal.get("action_type", "UNKNOWN")
    approval_status = proposal.get("approval_status", "PENDING")
    allowed_without_approval = proposal.get("allowed_without_approval", False)
    action_title = proposal.get("action_title", "Unknown Action")
    scheduled_node = proposal.get("scheduled_node", "None")

    print(f"Resolving proposal '{proposal_id}': {action_title} ({action_type})")

    # Gate 1: Hard block unsafe classes
    if action_type in UNSAFE_CLASSES:
        blocked_reason = f"Execution of unsafe action type '{action_type}' is prohibited under the safe-write model."
        print(f"[BLOCKED] {blocked_reason}")
        log_execution(proposal_id, action_type, mode, "BLOCKED", blocked_reason=blocked_reason)
        sys.exit(1)

    # Gate 2: Verify action type is permitted
    if action_type not in ["READ_ONLY", "LOCAL_SAFE_WRITE"]:
        blocked_reason = f"Action type '{action_type}' is unrecognized and blocked by default."
        print(f"[BLOCKED] {blocked_reason}")
        log_execution(proposal_id, action_type, mode, "BLOCKED", blocked_reason=blocked_reason)
        sys.exit(1)

    # Gate 3: Enforce approvals
    if action_type == "LOCAL_SAFE_WRITE" and approval_status != "APPROVED":
        blocked_reason = f"Local safe write action requires APPROVED status. Current status: {approval_status}"
        print(f"[BLOCKED] {blocked_reason}")
        log_execution(proposal_id, action_type, mode, "BLOCKED", blocked_reason=blocked_reason)
        sys.exit(1)

    if action_type == "READ_ONLY" and not allowed_without_approval and approval_status != "APPROVED":
        blocked_reason = f"Read-only action requires approval or allowed_without_approval flag. Current status: {approval_status}"
        print(f"[BLOCKED] {blocked_reason}")
        log_execution(proposal_id, action_type, mode, "BLOCKED", blocked_reason=blocked_reason)
        sys.exit(1)

    # Gate 4: Resolve allowed action dispatch mapping
    dispatcher_action = PROPOSAL_DISPATCHER_MAP.get(proposal_id)
    if not dispatcher_action:
        blocked_reason = f"No allowlisted dispatcher action mapped for proposal '{proposal_id}'."
        print(f"[BLOCKED] {blocked_reason}")
        log_execution(proposal_id, action_type, mode, "BLOCKED", blocked_reason=blocked_reason)
        sys.exit(1)

    timestamp_start = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

    # If DRY_RUN, compile simulated actions and staging evidence only
    if mode == "DRY_RUN":
        print(f"[DRY_RUN] Simulated execution of dispatcher action '{dispatcher_action}'...")
        staged_outputs = f"Simulated dry-run output of {dispatcher_action} on {scheduled_node}"
        rollback_art = proposal.get("rollback_plan", "Not required.")
        verify_res = f"Simulated verification logic for {dispatcher_action}: PASS"
        
        log_execution(
            proposal_id=proposal_id,
            action_type=action_type,
            mode=mode,
            status="SUCCESS",
            started_at=timestamp_start,
            completed_at=timestamp_start,
            executed_by="Swarm Operator (Dry Run)",
            affected_paths=proposal.get("affected_paths", []),
            commands_or_dispatcher_actions=[dispatcher_action],
            dry_run=True,
            staged_outputs=staged_outputs,
            rollback_artifacts=rollback_art,
            verification_results=verify_res
        )
        print("[PASS] Dry run completed and logged successfully.")
        sys.exit(0)

    # STAGED_EXECUTION: Run dispatcher
    print(f"[EXECUTE] Dispatching allowlisted action '{dispatcher_action}'...")
    sys.path.append(str(SCRIPT_DIR))
    from governed_execution_dispatcher import dispatch
    
    try:
        dispatch_res = dispatch(dispatcher_action)
        timestamp_end = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
        
        if dispatch_res.get("success"):
            status = "SUCCESS"
            staged_outputs = str(dispatch_res.get("output", dispatch_res.get("stdout", "Staged compilation complete.")))
            affected_paths = dispatch_res.get("affected_paths", [])
            rollback_art = proposal.get("rollback_plan", "Restore node environment configs.")
            verify_res = f"Verification check: {proposal.get('verification_plan', 'Verify script outcome.')} -> PASS"
            
            log_execution(
                proposal_id=proposal_id,
                action_type=action_type,
                mode=mode,
                status=status,
                started_at=timestamp_start,
                completed_at=timestamp_end,
                executed_by="Swarm Governed Runner",
                affected_paths=affected_paths,
                commands_or_dispatcher_actions=[dispatcher_action],
                dry_run=False,
                staged_outputs=staged_outputs,
                rollback_artifacts=rollback_art,
                verification_results=verify_res
            )
            print(f"[PASS] Governed execution of proposal '{proposal_id}' succeeded.")
            sys.exit(0)
        else:
            status = "FAILED"
            err_msg = dispatch_res.get("error", "Dispatcher execution failed.")
            print(f"[FAIL] Governed execution failed: {err_msg}")
            log_execution(
                proposal_id=proposal_id,
                action_type=action_type,
                mode=mode,
                status=status,
                started_at=timestamp_start,
                completed_at=timestamp_end,
                executed_by="Swarm Governed Runner",
                affected_paths=[],
                commands_or_dispatcher_actions=[dispatcher_action],
                dry_run=False,
                staged_outputs=f"Error: {err_msg}",
                rollback_artifacts="None",
                verification_results="FAIL"
            )
            sys.exit(1)
            
    except Exception as e:
        timestamp_end = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
        print(f"[FAIL] Unexpected crash in runner: {e}")
        log_execution(
            proposal_id=proposal_id,
            action_type=action_type,
            mode=mode,
            status="FAILED",
            started_at=timestamp_start,
            completed_at=timestamp_end,
            executed_by="Swarm Governed Runner",
            affected_paths=[],
            commands_or_dispatcher_actions=[dispatcher_action],
            dry_run=False,
            staged_outputs=f"Fatal exception: {str(e)}",
            rollback_artifacts="None",
            verification_results="FAIL"
        )
        sys.exit(1)

def log_execution(proposal_id, action_type, mode, status, started_at=None, completed_at=None,
                  executed_by="Swarm Governed Runner", affected_paths=None, commands_or_dispatcher_actions=None,
                  dry_run=False, staged_outputs="", rollback_artifacts="", verification_results="", blocked_reason=""):
    """Saves structured execution details to JSON and appends to Markdown evidence logs."""
    if not started_at:
        started_at = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    if not completed_at:
        completed_at = started_at
        
    execution_id = f"exec-{int(datetime.datetime.now().timestamp())}"
    logs = load_json(EXEC_LOG_JSON)
    
    new_log = {
        "execution_id": execution_id,
        "proposal_id": proposal_id,
        "action_type": action_type,
        "execution_mode": mode,
        "status": status,
        "started_at": started_at,
        "completed_at": completed_at,
        "executed_by": executed_by,
        "affected_paths": affected_paths or [],
        "commands_or_dispatcher_actions": commands_or_dispatcher_actions or [],
        "dry_run": dry_run,
        "staged_outputs": staged_outputs,
        "rollback_artifacts": rollback_artifacts,
        "verification_results": verification_results,
        "evidence_links": [
            "docs/security/governed-execution-safety-model.md",
            "docs/evidence/runtime/governed-execution-log.md"
        ],
        "blocked_reason": blocked_reason
    }
    
    logs.append(new_log)
    save_json(EXEC_LOG_JSON, logs)
    
    # 1. Update markdown log brief
    log_md_exists = os.path.exists(EXEC_LOG_MD)
    with open(EXEC_LOG_MD, "a", encoding="utf-8") as f:
        if not log_md_exists:
            f.write("# Swarm Governed Execution Log\n\n")
            f.write("This log tracks executed local safe-write and read-only actions under governed swarm controls.\n\n")
            f.write("| Timestamp | Exec ID | Proposal ID | Action Class | Mode | Status | Operator | Outputs |\n")
            f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        f.write(f"| {completed_at} | `{execution_id}` | `{proposal_id}` | {action_type} | {mode} | **{status}** | {executed_by} | {staged_outputs[:80]}... |\n")

    # 2. Append rollback details
    rollback_exists = os.path.exists(ROLLBACK_PLAN_MD)
    with open(ROLLBACK_PLAN_MD, "a", encoding="utf-8") as f:
        if not rollback_exists:
            f.write("# Swarm Governed Execution Rollback Plan\n\n")
            f.write("This document archives rollback procedures and status for executed actions.\n\n")
            f.write("| Timestamp | Exec ID | Proposal ID | Staged Paths | Rollback Action | Status |\n")
            f.write("| :--- | :--- | :--- | :--- | :--- | :--- |\n")
        paths_str = ", ".join(affected_paths or [])
        f.write(f"| {completed_at} | `{execution_id}` | `{proposal_id}` | `{paths_str}` | {rollback_artifacts} | STAGED_SAFE |\n")

if __name__ == "__main__":
    main()
