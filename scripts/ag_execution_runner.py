#!/usr/bin/env python3
import os
import sys
import json
import hashlib
import datetime
import traceback
from pathlib import Path

# Add scripts directory to path to allow importing LeaseManager
sys.path.append(str(Path(__file__).resolve().parent))
from ag_execution_lease_manager import LeaseManager

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "has_live_project_tracker/data"
QUEUE_FILE = DATA_DIR / "helm_task_queue.json"
CONTROL_FILE = DATA_DIR / "orchestration_bridge_control.json"
LOG_FILE = DATA_DIR / "helm_execution_log.json"
STATE_FILE = DATA_DIR / "ag_execution_adapter_state.json"
HOLD_FILE = DATA_DIR / "ag_operator_hold.json"
RETRY_POLICY_FILE = DATA_DIR / "ag_execution_retry_policy.json"
POLICY_FILE = DATA_DIR / "ag_execution_policy.json"
FAILURES_FILE = DATA_DIR / "ag_execution_failures.jsonl"
PROOF_INDEX_FILE = DATA_DIR / "ag_execution_proof_index.json"
HANDOFF_QUEUE_FILE = DATA_DIR / "founder_handoff_queue.json"

RUNNER_VERSION = "1.1.0"


def stage_for_founder(task, policy_category, reason):
    """DOORSTEP posture: park a door-crossing task in the shared founder handoff
    queue as READY_FOR_FOUNDER instead of silently dropping it. Idempotent by
    task_id so repeated cycles don't duplicate. This never crosses the door —
    it only records that the work is staged and waiting on founder revenue
    activation."""
    hq = load_json(HANDOFF_QUEUE_FILE, {
        "schema_version": "1.0",
        "queue_purpose": "DOORSTEP staging — factory work parked at the pre-purchase door awaiting founder revenue activation",
        "exit_condition": "FOUNDER_ACTIVATES_REVENUE",
        "staged": [],
    })
    staged = hq.setdefault("staged", [])
    tid = task.get("task_id")
    if any(s.get("task_id") == tid for s in staged):
        return  # already parked
    staged.append({
        "task_id": tid,
        "task_name": task.get("task_name", "Unknown task"),
        "task_class": task.get("task_class", "unknown"),
        "factory": task.get("factory") or task.get("allowed_agent") or "unknown",
        "policy_category": policy_category,
        "status": "READY_FOR_FOUNDER",
        "reason": reason,
        "staged_at": get_utc_now(),
        "exit_condition": "FOUNDER_ACTIVATES_REVENUE",
    })
    save_json(HANDOFF_QUEUE_FILE, hq)
    log_message(f"🚪 DOORSTEP: staged task {tid} for founder ({policy_category}). Handoff queue depth: {len(staged)}")

def get_utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

def log_message(msg):
    print(f"[{get_utc_now()}] [AG-EXECUTOR] {msg}")

def load_json(path, default):
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return default

def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def compute_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def update_runner_state(next_state: str, task_id: str = None, reason: str = None, evidence_path: str = None):
    state_data = load_json(STATE_FILE, {"status": "IDLE", "transitions": []})
    prev_state = state_data.get("status", "IDLE")
    
    transition = {
        "timestamp": get_utc_now(),
        "task_id": task_id,
        "previous_state": prev_state,
        "next_state": next_state,
        "reason": reason or "",
        "evidence_path": evidence_path or ""
    }
    
    state_data["status"] = next_state
    state_data["current_task"] = task_id
    state_data["last_execution_at"] = get_utc_now()
    if "transitions" not in state_data:
        state_data["transitions"] = []
    state_data["transitions"].append(transition)
    
    save_json(STATE_FILE, state_data)
    log_message(f"State transition: {prev_state} -> {next_state} (Task: {task_id}, Reason: {reason})")

def run_executor():
    # 1. Operator Hold Check
    hold_data = load_json(HOLD_FILE, {"operator_hold_active": False})
    if hold_data.get("operator_hold_active"):
        log_message(f"❌ Operator Hold is active. Reason: {hold_data.get('reason')}. Skipping execution.")
        update_runner_state("BLOCKED_BY_POLICY", reason="Operator Hold is active")
        sys.exit(0)

    # 2. Check control switch
    control = load_json(CONTROL_FILE, {})
    if not control.get("allow_ag_execution"):
        log_message("AG Execution not allowed yet. Skipping.")
        sys.exit(0)

    # 3. Load task queue
    queue = load_json(QUEUE_FILE, [])
    pending_tasks = [
        t for t in queue 
        if t.get("status") in ["PENDING", "RETRY_PENDING"] and (t.get("allowed_agent") == "hasf_builder_agent" or t.get("adapter") == "ag_execution_adapter")
    ]
    
    if not pending_tasks:
        log_message("No pending executor tasks found.")
        update_runner_state("IDLE")
        sys.exit(0)

    # Load retry policy and execution policies
    retry_policy = load_json(RETRY_POLICY_FILE, {"max_retries": 3, "non_retryable_categories": []})
    execution_policy = load_json(POLICY_FILE, {"policy_categories": {}})
    
    lm = LeaseManager()
    
    for task in pending_tasks:
        task_id = task.get("task_id")
        task_name = task.get("task_name", "Unknown task")
        task_class = task.get("task_class", "unknown")
        attempts = task.get("attempts", 0)
        
        log_message(f"Attempting to acquire lease for task {task_id}: {task_name}")
        lease = lm.acquire_lease(task_id, "ag_execution_runner")
        if not lease:
            log_message(f"[-] Could not acquire lease for task {task_id}. Skipping.")
            continue
            
        lease_id = lease["lease_id"]
        update_runner_state("LEASE_ACQUIRED", task_id=task_id, reason="Acquired lock")
        
        # Fencing Token check
        fencing_token = lease.get("fencing_token", 0)
        proof_index = load_json(PROOF_INDEX_FILE, {"proofs": []})
        max_existing_token = 0
        for entry in proof_index.get("proofs", []):
            t_token = entry.get("fencing_token", 0)
            if t_token > max_existing_token:
                max_existing_token = t_token
                
        if fencing_token <= max_existing_token:
            log_message(f"❌ Fencing token violation: lease token {fencing_token} is stale (max existing: {max_existing_token}). Rejecting write.")
            task["status"] = "BLOCKED"
            save_json(QUEUE_FILE, queue)
            lm.release_lease(lease_id, status="FAILED")
            update_runner_state("BLOCKED_BY_POLICY", task_id=task_id, reason="Fencing token is stale")
            continue
        
        # Determine policy category and check safety bounds
        policy_category = "requires_michael_approval"
        is_allowed = False
        
        # Check against policy file rules
        for cat_name, cat_rule in execution_policy.get("policy_categories", {}).items():
            if cat_name.startswith("allowed_"):
                prefixes = cat_rule.get("action_prefixes", [])
                if any(task_name.lower().startswith(p) or task_class.lower().startswith(p) for p in prefixes):
                    policy_category = cat_name
                    is_allowed = True
                    break
            elif cat_name.startswith("blocked_") or cat_name == "requires_michael_approval":
                keywords = cat_rule.get("keywords", [])
                if any(k in task_name.lower() or k in task_class.lower() for k in keywords):
                    policy_category = cat_name
                    is_allowed = False
                    break
                    
        log_message(f"Task classified as {policy_category}. Allowed: {is_allowed}")
        
        if not is_allowed:
            # DOORSTEP posture: park door-crossing work for the founder instead of
            # dropping it. The money/credential/publish gates are NOT crossed here —
            # the task is only staged as READY_FOR_FOUNDER. Genuinely unsafe
            # categories (destructive actions) are hard-blocked and never staged.
            posture = control.get("execution_posture", "DEFAULT")
            doorstep = control.get("doorstep_policy", {})
            door_categories = set(doorstep.get("door_categories", []))
            hard_block_categories = set(doorstep.get("hard_block_categories", ["blocked_destructive_action"]))

            if posture == "DOORSTEP" and policy_category in door_categories and policy_category not in hard_block_categories:
                reason = "DOORSTEP: staged at pre-purchase door, awaiting founder revenue activation"
                log_message(f"🚪 Policy category {policy_category} is a door-crossing action. Staging for founder.")
                stage_for_founder(task, policy_category, reason)
                task["status"] = "STAGED_FOR_FOUNDER"
                task["policy_category"] = policy_category
                save_json(QUEUE_FILE, queue)
                lm.release_lease(lease_id, status="RELEASED")
                update_runner_state("BLOCKED_BY_POLICY", task_id=task_id, reason=reason)
                continue

            log_message(f"❌ Policy check failed for category {policy_category}.")
            task["status"] = "BLOCKED"
            task["policy_category"] = policy_category
            save_json(QUEUE_FILE, queue)
            lm.release_lease(lease_id, status="FAILED")
            update_runner_state("BLOCKED_BY_POLICY", task_id=task_id, reason=f"Task classified as {policy_category}")
            continue
            
        # Start executing
        update_runner_state("EXECUTING", task_id=task_id, reason="Execution started")
        task["attempts"] = attempts + 1
        
        try:
            # REAL execution — the agent actually performs the task with tools and returns
            # real evidence (full transcript + artifacts + real hashes). This REPLACES the
            # prior fabricated-proof stub ("Generated code structure blueprints…") that wrote
            # a fake SUCCESS proof while doing nothing. This is the engine the swarm lacked.
            import sys as _sys
            if str(ROOT) not in _sys.path:
                _sys.path.insert(0, str(ROOT))
            from backend.agent_executor import execute_task as _agent_execute

            _res = _agent_execute(task)
            input_hash = _res["input_hash"]
            output_hash = _res["output_hash"]
            proof_file = ROOT / _res["evidence_path"]
            log_message(f"Agent executed {task_id}: {_res['status']} — "
                        f"{_res['summary'][:100]} (artifacts: {_res['artifacts']})")
            if _res["status"] != "SUCCESS":
                # Not an exception, but not finished — hand to the retry machinery below.
                raise RuntimeError(f"agent execution INCOMPLETE: {_res['summary'][:150]}")

            # Log to execution log
            logs = load_json(LOG_FILE, [])
            log_entry = {
                "event": "ag_task_executed",
                "task_id": task_id,
                "task_name": task_name,
                "timestamp": get_utc_now(),
                "status": "SUCCESS",
                "evidence_hash": output_hash
            }
            logs.append(log_entry)
            save_json(LOG_FILE, logs)
            
            # Add to Proof Index
            proof_index = load_json(PROOF_INDEX_FILE, {"proofs": []})
            proof_entry = {
                "task_id": task_id,
                "lease_id": lease_id,
                "fencing_token": fencing_token,
                "input_hash": input_hash,
                "output_hash": output_hash,
                "timestamp": get_utc_now(),
                "status": "SUCCESS",
                "evidence_path": f"docs/evidence/runtime/ag_execution_proof_{task_id}.md"
            }
            proof_index["proofs"].append(proof_entry)
            save_json(PROOF_INDEX_FILE, proof_index)

            # Write markdown proof file to satisfy validators/tests
            md_path = ROOT / proof_entry["evidence_path"]
            md_path.parent.mkdir(parents=True, exist_ok=True)
            md_path.write_text(f"# AG Execution Proof: {task_id}\nStatus: SUCCESS\nInput Hash: {input_hash}\nOutput Hash: {output_hash}\n", encoding="utf-8")
            
            task["status"] = "completed"
            task["completed_at"] = get_utc_now()
            task["result"] = f"file://{md_path}"
            task["policy_category"] = policy_category
            task["fencing_token"] = fencing_token
            save_json(QUEUE_FILE, queue)
            
            lm.release_lease(lease_id, status="RELEASED")
            update_runner_state("COMPLETED", task_id=task_id, reason="Execution success", evidence_path=str(proof_file))
            log_message(f"🟢 Task {task_id} successfully executed.")
            
        except Exception as e:
            tb = traceback.format_exc()
            log_message(f"❌ Execution failed for task {task_id}: {e}")
            
            # Manage Retry bounds
            max_retries = retry_policy.get("max_retries", 3)
            current_attempts = task["attempts"]
            
            is_retryable = policy_category not in retry_policy.get("non_retryable_categories", [])
            
            if current_attempts < max_retries and is_retryable:
                task["status"] = "RETRY_PENDING"
                save_json(QUEUE_FILE, queue)
                lm.release_lease(lease_id, status="FAILED")
                update_runner_state("RETRY_PENDING", task_id=task_id, reason=f"Attempts {current_attempts}/{max_retries}. Error: {e}")
            else:
                task["status"] = "FAILED"
                save_json(QUEUE_FILE, queue)
                
                # Write to failure ledger
                with open(FAILURES_FILE, "a", encoding="utf-8") as ff:
                    failure_entry = {
                        "task_id": task_id,
                        "task_name": task_name,
                        "timestamp": get_utc_now(),
                        "attempts": current_attempts,
                        "error": str(e),
                        "traceback": tb
                    }
                    ff.write(json.dumps(failure_entry) + "\n")
                    
                lm.release_lease(lease_id, status="FAILED")
                update_runner_state("FAILED", task_id=task_id, reason=f"Task permanent failure. Error: {e}")
                
if __name__ == "__main__":
    run_executor()
