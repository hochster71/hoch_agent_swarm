#!/usr/bin/env python3
import os
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "has_live_project_tracker/data"
LEDGER_FILE = DATA_DIR / "ag_execution_burn_in_ledger.jsonl"
ORACLE_FILE = DATA_DIR / "ag_execution_burn_in_oracle.json"
PROOF_INDEX_FILE = DATA_DIR / "ag_execution_proof_index.json"
QUEUE_FILE = DATA_DIR / "helm_task_queue.json"
HEARTBEAT_STATUS_FILE = DATA_DIR / "ag_daemon_heartbeat_status.json"

def main():
    print("Executing master AG Execution Burn-In Validator...")
    
    if not ORACLE_FILE.exists():
        print("❌ Oracle configuration file missing!")
        sys.exit(1)
        
    with open(ORACLE_FILE, "r") as f:
        oracle = json.load(f)
        
    # Read raw ledger
    raw_lines = []
    if LEDGER_FILE.exists():
        with open(LEDGER_FILE, "r") as f:
            for line in f:
                if line.strip():
                    raw_lines.append(json.loads(line))
                    
    real_cycles = [r for r in raw_lines if not r.get("simulated")]
    simulated_cycles = [r for r in raw_lines if r.get("simulated")]
    
    # Re-compute counts
    completed_task_ids = set()
    duplicate_executions = 0
    
    queue = []
    if QUEUE_FILE.exists():
        with open(QUEUE_FILE, "r") as f:
            queue = json.load(f)
            
    for task in queue:
        t_id = task.get("task_id") or task.get("id")
        if not t_id:
            continue
        if task.get("status") == "completed":
            if t_id in completed_task_ids:
                duplicate_executions += 1
            completed_task_ids.add(t_id)
            
    # Check completed to proof 1:1 crosswalk
    proof_index = {}
    if PROOF_INDEX_FILE.exists():
        with open(PROOF_INDEX_FILE, "r") as f:
            proof_index = json.load(f)
            
    proofs = proof_index.get("proofs", [])
    proof_task_ids = {p["task_id"] for p in proofs}
    
    missing_proofs = 0
    for t_id in completed_task_ids:
        # Check if the task is an autonomy runner task
        is_autonomy = any(t.get("task_id") == t_id and (t.get("allowed_agent") == "hasf_builder_agent" or t.get("adapter") == "ag_execution_adapter") for t in queue)
        if is_autonomy and t_id not in proof_task_ids:
            print(f"❌ Completed task {t_id} is missing its proof file!")
            missing_proofs += 1
            
    # Check heartbeat observer freshness
    hb_fresh = True
    if HEARTBEAT_STATUS_FILE.exists():
        with open(HEARTBEAT_STATUS_FILE, "r") as f:
            hb_data = json.load(f)
        if hb_data.get("verdict") in ["HEARTBEAT_STALE", "HEARTBEAT_MISSING"]:
            hb_fresh = False
            
    # Verify all required Phase E files exist
    required_files = [
        "docs/autonomy/AG_EXECUTION_BURN_IN_ORACLE.md",
        "has_live_project_tracker/data/ag_execution_burn_in_oracle.json",
        "scripts/ag_execution_daemon.py",
        "docs/autonomy/AG_EXECUTION_DAEMON.md",
        "has_live_project_tracker/data/ag_execution_daemon_state.json",
        "scripts/verify_daemon_heartbeat.py",
        "has_live_project_tracker/data/ag_daemon_heartbeat_status.json",
        "has_live_project_tracker/data/ag_execution_burn_in_ledger.jsonl",
        "has_live_project_tracker/data/ag_execution_burn_in_summary.json",
        "docs/autonomy/AG_EXECUTION_LEASE_FENCING.md",
        "scripts/verify_ag_execution_fencing.py",
        "has_live_project_tracker/data/ag_execution_fencing_status.json",
        "scripts/ag_execution_failure_injector.py",
        "docs/autonomy/AG_EXECUTION_FAILURE_INJECTION.md",
        "has_live_project_tracker/data/ag_execution_injection_schedule.json",
        "has_live_project_tracker/data/ag_execution_injection_results.jsonl",
        "scripts/ag_execution_supervision_test.py",
        "has_live_project_tracker/data/ag_execution_supervision_test.json",
        "docs/autonomy/AG_EXECUTION_SUPERVISION_PROOF.md",
        "scripts/verify_ag_execution_burn_in.py",
        "docs/autonomy/PHASE_E_AUTONOMY_DAEMON_BURN_IN_REPORT.md"
    ]
    missing_files = [f for f in required_files if not (ROOT / f).exists()]
    if missing_files:
        print(f"⚠️ Missing required Phase E files: {missing_files}")

    # Calculate elapsed hours
    from datetime import datetime
    timestamps = []
    for row in raw_lines:
        ts_str = row.get("timestamp")
        if ts_str:
            try:
                clean_ts = ts_str.rstrip("Z").split("+")[0]
                timestamps.append(datetime.fromisoformat(clean_ts))
            except Exception:
                pass
    elapsed_hours = 0.0
    if timestamps:
        elapsed_hours = (max(timestamps) - min(timestamps)).total_seconds() / 3600.0

    # Validate rules
    failed_real = len([r for r in real_cycles if r.get("verdict") == "FAIL"])
    failed_rate = float(failed_real) / max(1, len(real_cycles))
    
    has_violations = (
        duplicate_executions > oracle["max_duplicate_executions"] or
        missing_proofs > oracle["max_missing_proofs"] or
        failed_rate > oracle["max_failed_cycle_rate"]
    )

    # Determine verdict
    if has_violations:
        phase_e_verdict = "RUNTIME_PROOF_NO_GO"
        verdict = "RUNTIME_PROOF_NO_GO"
    elif len(real_cycles) >= oracle["min_real_cycles"] and hb_fresh:
        if elapsed_hours >= 72.0:
            phase_e_verdict = "PHASE_E_72H_GO"
            verdict = "RUNTIME_PROOF_GO"
        elif elapsed_hours >= 24.0:
            phase_e_verdict = "PHASE_E_24H_GO"
            verdict = "RUNTIME_PROOF_GO"
        else:
            phase_e_verdict = "PHASE_E_REAL_BURN_IN_PENDING"
            verdict = "RUNTIME_PROOF_CONDITIONAL_GO"
    elif len(simulated_cycles) > 0:
        phase_e_verdict = "PHASE_E_TEST_MODE_GO"
        verdict = "RUNTIME_PROOF_CONDITIONAL_GO"
    else:
        phase_e_verdict = "PHASE_E_INFRASTRUCTURE_GO"
        verdict = "RUNTIME_PROOF_CONDITIONAL_GO"
        
    # Count injections
    injection_cycles = 0
    injection_results_file = DATA_DIR / "ag_execution_injection_results.jsonl"
    if injection_results_file.exists():
        with open(injection_results_file, "r") as f:
            for line in f:
                if line.strip():
                    injection_cycles += 1

    print(f"Verdict derived: {verdict}")
    print(f"Phase E Verdict: {phase_e_verdict}")
    print(f"  Real Cycles: {len(real_cycles)}")
    print(f"  Simulated Cycles: {len(simulated_cycles)}")
    print(f"  Injection Cycles: {injection_cycles}")
    print(f"  Duplicates: {duplicate_executions}")
    print(f"  Missing Proofs: {missing_proofs}")
    print(f"  Failed Real Rate: {failed_rate:.2f}")
    print(f"  Elapsed Hours: {elapsed_hours:.4f}")
    
    # Save the Phase E verdict to summary JSON
    if DATA_DIR.exists():
        summary_path = DATA_DIR / "ag_execution_burn_in_summary.json"
        if summary_path.exists():
            try:
                with open(summary_path, "r") as f:
                    summary_data = json.load(f)
                summary_data["final_verdict"] = phase_e_verdict
                summary_data["lane_1_verdict"] = verdict
                summary_data["injection_cycles"] = injection_cycles
                with open(summary_path, "w") as f:
                    json.dump(summary_data, f, indent=2)
            except Exception:
                pass

    if verdict == "RUNTIME_PROOF_NO_GO":
        print("❌ AG Burn-In verification failed.")
        sys.exit(1)
        
    print("🟢 AG Burn-In verification succeeded.")
    print(f"✅ AG Burn-In verification PASSED with verdict: {verdict}")
    sys.exit(0)

if __name__ == "__main__":
    main()
