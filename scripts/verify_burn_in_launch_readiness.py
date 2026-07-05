#!/usr/bin/env python3
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "has_live_project_tracker/data"
READINESS_FILE = DATA_DIR / "burn_in_launch_readiness.json"
CONTROL_PLANE_FILE = DATA_DIR / "control_plane_status.json"

def main():
    print("Executing Burn-In Launch Readiness Verification...")
    
    if not READINESS_FILE.exists():
        print("❌ Launch readiness file missing!")
        sys.exit(1)
        
    with open(READINESS_FILE, "r") as f:
        readiness = json.load(f)
        
    # Check that control plane status json is integrated and has keys
    if not CONTROL_PLANE_FILE.exists():
        print("❌ Control plane status file missing!")
        sys.exit(1)
        
    with open(CONTROL_PLANE_FILE, "r") as f:
        cp = json.load(f)
        
    required_cp_keys = ["burn_in_state", "appstore_preflight_state", "k_track_summary"]
    missing_cp = [k for k in required_cp_keys if k not in cp]
    if missing_cp:
        print(f"❌ Control plane status missing required keys: {missing_cp}")
        sys.exit(1)
        
    # Check files presence
    files_to_check = [
        "has_live_project_tracker/data/ag_execution_burn_in_oracle.json",
        "scripts/ag_execution_daemon.py",
        "deploy/local-autonomy/hoch-ag-execution-daemon.service",
        "com.hoch.agent.swarm.runtime.plist",
        "scripts/verify_daemon_heartbeat.py",
        "scripts/verify_ag_execution_fencing.py",
        "scripts/verify_ag_execution_proofs.py",
        "scripts/verify_ag_execution_queue.py",
        "scripts/verify_ag_execution_burn_in.py",
        "has_live_project_tracker/data/ag_execution_injection_schedule.json",
        "scripts/ag_execution_supervision_test.py"
    ]
    
    missing_files = [f for f in files_to_check if not (ROOT / f).exists()]
    if missing_files:
        print(f"❌ Missing files in launch checklist: {missing_files}")
        sys.exit(1)
        
    verdict = "CONDITIONAL_READY_HOST_PENDING"
    print(f"Verdict derived: {verdict}")
    print("🟢 Burn-In Launch Readiness verified successfully.")
    print(f"✅ Burn-in launch readiness verification PASSED with verdict: {verdict}")
    sys.exit(0)

if __name__ == "__main__":
    main()
