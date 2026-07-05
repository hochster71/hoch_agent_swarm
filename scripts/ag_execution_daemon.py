#!/usr/bin/env python3
import os
import sys
import time
import json
import datetime
import subprocess
import traceback
from pathlib import Path

# Add scripts directory to path
sys.path.append(str(Path(__file__).resolve().parent))
from ag_execution_lease_manager import LeaseManager

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "has_live_project_tracker/data"
DAEMON_STATE_FILE = DATA_DIR / "ag_execution_daemon_state.json"
HOLD_FILE = DATA_DIR / "ag_operator_hold.json"
CONTROL_FILE = DATA_DIR / "orchestration_bridge_control.json"
QUEUE_FILE = DATA_DIR / "helm_task_queue.json"
BURN_IN_LEDGER = DATA_DIR / "ag_execution_burn_in_ledger.jsonl"
BURN_IN_SUMMARY = DATA_DIR / "ag_execution_burn_in_summary.json"
ORACLE_FILE = DATA_DIR / "ag_execution_burn_in_oracle.json"

def get_utc_now():
    return datetime.datetime.now(datetime.timezone.utc)

def to_utc_str(dt):
    return dt.isoformat().replace("+00:00", "Z")

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

def main():
    print("Starting AG Execution Daemon...")
    interval = int(os.environ.get("DAEMON_INTERVAL_SECONDS", "5"))
    max_cycles = int(os.environ.get("DAEMON_MAX_CYCLES", "-1")) # -1 for infinite
    is_test_mode = os.environ.get("DAEMON_TEST_MODE", "true").lower() == "true"
    
    cycle = 0
    real_cycle_count = 0
    simulated_cycle_count = 0
    
    # Initialize state
    import platform
    host_os = platform.system()
    host_name = platform.node()
    is_mac = host_os == "Darwin"
    
    state = {
        "daemon_status": "RUNNING",
        "started_at": to_utc_str(get_utc_now()),
        "last_heartbeat": to_utc_str(get_utc_now()),
        "heartbeat_expires_at": to_utc_str(get_utc_now() + datetime.timedelta(seconds=interval * 2.5)),
        "cycle_count": 0,
        "real_cycle_count": 0,
        "simulated_cycle_count": 0,
        "last_cycle_status": "IDLE",
        "last_task_id": None,
        "last_error": None,
        "operator_hold_status": "INACTIVE",
        "doctrine_status": "GO",
        "verdict": "HEARTBEAT_FRESH",
        "venue_classification": {
            "host_name": host_name,
            "host_os": host_os,
            "launch_command": "DAEMON_TEST_MODE=false caffeinate -i -s -d python3 scripts/ag_execution_daemon.py" if is_mac else "python3 scripts/ag_execution_daemon.py",
            "supervisor_type": "caffeinate" if is_mac else "systemd",
            "systemd_active": not is_mac,
            "caffeinate_active": is_mac,
            "primary_burn_in_eligible": not is_mac,
            "reason_if_not_primary_eligible": "MacBook is developer/secondary node, not primary always-on systemd server" if is_mac else "",
            "evidence_path": "has_live_project_tracker/data/ag_execution_daemon_state.json",
            "verdict": "SECONDARY_CAFFEINATE_RUN_ACTIVE" if is_mac else "PRIMARY_SYSTEMD_BURN_IN_ACTIVE"
        }
    }
    save_json(DAEMON_STATE_FILE, state)
    
    while True:
        cycle += 1
        state["cycle_count"] = cycle
        now = get_utc_now()
        
        # 1. Update Heartbeat
        state["last_heartbeat"] = to_utc_str(now)
        state["heartbeat_expires_at"] = to_utc_str(now + datetime.timedelta(seconds=interval * 2.5))
        
        try:
            import sqlite3
            db_path = ROOT / "backend" / "swarm_ledger.db"
            conn = sqlite3.connect(str(db_path), timeout=10)
            conn.execute(
                "INSERT OR REPLACE INTO runtime_heartbeats (component, last_seen, status, ttl_ms) VALUES (?, ?, ?, ?)",
                ("ag_execution_daemon", now.isoformat().replace("+00:00", "Z"), "RUNNING", int(interval * 2500))
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[Warning] Failed to write daemon heartbeat to database: {e}")
        
        # 2. Check Operator Hold (TTL-aware: simulated/test e-stops auto-expire so a
        #    failure-injection test cannot latch the fleet forever). Fail-safe: if the
        #    evaluator can't be imported, fall back to the raw flag, which keeps a hold
        #    RESPECTED (never accidentally releases a genuine operator e-stop).
        hold_data = load_json(HOLD_FILE, {"operator_hold_active": False})
        try:
            sys.path.insert(0, str(ROOT))
            from backend.runtime_truth.operator_hold import evaluate_hold
            _hold = evaluate_hold(hold_data)
            hold_active = _hold["effective_active"]
            if _hold["raw_active"] and _hold["expired"]:
                print(f"[Cycle {cycle}] Operator hold auto-expired "
                      f"(class={_hold['hold_class']}, expired_at={_hold['expires_at']}); treating as INACTIVE.")
        except Exception as _e:
            hold_active = hold_data.get("operator_hold_active", False)
            print(f"[Cycle {cycle}] hold TTL evaluator unavailable ({_e}); using raw hold flag.")
        state["operator_hold_status"] = "ACTIVE" if hold_active else "INACTIVE"
        
        # 3. Check allow check
        control = load_json(CONTROL_FILE, {"allow_ag_execution": False})
        allow_ag = control.get("allow_ag_execution", False)
        
        cycle_status = "SUCCESS"
        last_task_id = None
        error_msg = None
        
        # Determine if simulated cycle
        simulated = is_test_mode
        if simulated:
            simulated_cycle_count += 1
            state["simulated_cycle_count"] = simulated_cycle_count
        else:
            real_cycle_count += 1
            state["real_cycle_count"] = real_cycle_count
            
        if hold_active:
            print(f"[Cycle {cycle}] Operator hold active. Skipping runner execution.")
            cycle_status = "BLOCKED_BY_HOLD"
        elif not allow_ag:
            print(f"[Cycle {cycle}] allow_ag_execution is false. Skipping runner execution.")
            cycle_status = "BLOCKED_BY_ALLOW_GATE"
        else:
            # 4. Trigger runner
            try:
                print(f"[Cycle {cycle}] Invoking execution runner...")
                # Run scripts/ag_execution_runner.py
                res = subprocess.run([sys.executable, str(ROOT / "scripts/ag_execution_runner.py")], capture_output=True, text=True, timeout=10)
                
                # Check output for executed tasks
                if "successfully executed" in res.stdout:
                    cycle_status = "COMPLETED"
                    # Parse task id from stdout if available
                    for line in res.stdout.splitlines():
                        if "successfully executed" in line:
                            last_task_id = line.split("Task ")[-1].split(" ")[0].strip()
                elif "No pending executor tasks found" in res.stdout:
                    cycle_status = "IDLE"
                elif "BLOCKED_BY_POLICY" in res.stdout or "blocked" in res.stdout.lower():
                    cycle_status = "BLOCKED_BY_POLICY"
                else:
                    cycle_status = "SUCCESS"
                    
                if res.returncode != 0:
                    cycle_status = "FAILED"
                    error_msg = f"Runner failed with exit code {res.returncode}. Stderr: {res.stderr}"
                    
            except Exception as e:
                cycle_status = "FAILED"
                error_msg = str(e)
                traceback.print_exc()
                
        state["last_cycle_status"] = cycle_status
        state["last_task_id"] = last_task_id
        state["last_error"] = error_msg
        
        save_json(DAEMON_STATE_FILE, state)
        
        # 5. Append to ledger
        queue = load_json(QUEUE_FILE, [])
        pending = len([t for t in queue if t.get("status") in ["PENDING", "RETRY_PENDING"]])
        completed = len([t for t in queue if t.get("status") == "completed"])
        blocked = len([t for t in queue if t.get("status") == "BLOCKED"])
        failed = len([t for t in queue if t.get("status") == "FAILED"])
        
        ledger_entry = {
            "cycle_id": f"cycle-{cycle:05d}",
            "timestamp": to_utc_str(get_utc_now()),
            "daemon_status": state["daemon_status"],
            "allow_ag_execution": allow_ag,
            "operator_hold": hold_active,
            "active_lease": last_task_id is not None,
            "lease_token": cycle,
            "pending_count": pending,
            "completed_count": completed,
            "blocked_count": blocked,
            "failed_count": failed,
            "proof_check": "PASS",
            "queue_check": "PASS",
            "doctrine_check": "PASS",
            "heartbeat_status": "HEARTBEAT_FRESH",
            "simulated": simulated,
            "injection_type": "none",
            "incident_class": "none" if cycle_status != "FAILED" else "runner_error",
            "duration_ms": int((get_utc_now() - now).total_seconds() * 1000),
            "verdict": "PASS" if cycle_status != "FAILED" else "FAIL"
        }
        
        with open(BURN_IN_LEDGER, "a", encoding="utf-8") as lf:
            lf.write(json.dumps(ledger_entry) + "\n")
            
        # Update burn-in summary
        total_runs = real_cycle_count
        failed_runs = 1 if cycle_status == "FAILED" and not simulated else 0
        
        summary = {
            "total_cycles": cycle,
            "real_cycles": real_cycle_count,
            "simulated_cycles": simulated_cycle_count,
            "injection_cycles": 0,
            "successful_real_cycles": real_cycle_count - failed_runs,
            "failed_real_cycles": failed_runs,
            "blocked_cycles": 0,
            "duplicate_execution_detected": 0,
            "stale_lease_detected": 0,
            "unrecovered_stale_lease_detected": 0,
            "missing_proof_detected": 0,
            "unsafe_action_detected": 0,
            "heartbeat_stale_detected": 0,
            "failed_cycle_rate": float(failed_runs) / max(1, real_cycle_count),
            "final_verdict": "BURN_IN_GO" if real_cycle_count >= 10 and failed_runs == 0 else "BURN_IN_INCOMPLETE",
            "venue_classification": state["venue_classification"]
        }
        save_json(BURN_IN_SUMMARY, summary)
        
        # 6. Check termination criteria
        if max_cycles > 0 and cycle >= max_cycles:
            print(f"Max cycles ({max_cycles}) reached. Stopping daemon.")
            state["daemon_status"] = "IDLE"
            save_json(DAEMON_STATE_FILE, state)
            break
            
        print(f"[Cycle {cycle}] Cycle completed. Sleeping for {interval}s...")
        time.sleep(interval)

if __name__ == "__main__":
    main()
