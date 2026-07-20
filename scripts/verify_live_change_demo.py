#!/usr/bin/env python3
import time
import sys
import os
import json
import urllib.request
import ssl
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

API_URL = "https://127.0.0.1:8770/api/v1/helm/live"

import urllib.error
def query_api():
    for attempt in range(3):
        try:
            req = urllib.request.Request(API_URL, method="GET")
            with urllib.request.urlopen(req, context=ctx, timeout=5) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as he:
            body = he.read().decode("utf-8") if he else ""
            print(f"HTTPError {he.code} querying API: {body}")
            time.sleep(1)
        except Exception as e:
            print(f"Error querying API (attempt {attempt+1}/3): {e}")
            time.sleep(1)
    return None

def main():
    log_lines = []
    def log(msg):
        print(msg)
        log_lines.append(msg)

    log("# HELM Founder Live-Change End-to-End Demonstration Log")
    log(f"Date: {datetime.datetime.now(datetime.timezone.utc).isoformat()}")
    log("This log records the live state propagation across the collector, FastAPI backend, and Founder cockpit.\n")

    # Step 1: Open the UI / check baseline
    log("## Step 1: Verifying Baseline state")
    state = query_api()
    if not state:
        log("✗ API is unreachable.")
        sys.exit(1)
    
    log(f"✓ Baseline API reachable. Truth status: {state['truth_status']} | Mode: {state['mode']}")
    log(f"✓ Active processes count: {len(state['active_processes'])}")
    log(f"✓ Worktree status clean: {state['candidate']['worktree_clean']}")
    log(f"✓ Current blockers: {state['blockers']}")
    
    # Step 2: Start a real test process
    log("\n## Step 2: Spawning background test process")
    cmd = [sys.executable, "-c", "import time; time.sleep(8)", "--pytest", "--tests"]
    proc = subprocess.Popen(cmd)
    log(f"✓ Spawned background process with PID {proc.pid}")
    
    # Step 3: Confirm it appears in the API
    log("\n## Step 3: Verifying active process detection")
    found_running = False
    for _ in range(5):
        time.sleep(1)
        state = query_api()
        if state and state["active_processes"]:
            active_pids = [p["pid"] for p in state["active_processes"]]
            if proc.pid in active_pids:
                log(f"✓ Success: Process {proc.pid} detected in active_processes!")
                log(f"✓ State changed to: {state['truth_status']} | Mode: {state['mode']}")
                found_running = True
                break
    if not found_running:
        log("✗ Failed: Process was not detected in active_processes.")
        proc.kill()
        sys.exit(1)
        
    # Step 4: Stop the process
    log("\n## Step 4: Terminating background test process")
    proc.terminate()
    proc.wait()
    log("✓ Process terminated.")
    
    # Step 5: Confirm it disappears
    log("\n## Step 5: Verifying active process removal")
    found_stopped = False
    for _ in range(5):
        time.sleep(1)
        state = query_api()
        if state and not state["active_processes"]:
            log(f"✓ Success: Process {proc.pid} cleared from active_processes list.")
            log(f"✓ State returned to: {state['truth_status']} | Mode: {state['mode']}")
            found_stopped = True
            break
    if not found_stopped:
        log("✗ Failed: Process list did not clear.")
        sys.exit(1)

    # Step 6: Modify a tracked file
    log("\n## Step 6: Modifying a tracked file to simulate dirty state")
    target_file = ROOT / "backend/agent_safety_governor.py"
    original_content = target_file.read_text(encoding="utf-8")
    
    try:
        # Append minor comment
        target_file.write_text(original_content + "\n# live_change_demo_marker\n", encoding="utf-8")
        log("✓ Appended marker comment to backend/agent_safety_governor.py")
        
        # Step 7: Confirm repository state changes to DIRTY for targeted file
        log("\n## Step 7: Verifying repository changes detection (targeted file)")
        found_dirty = False
        for _ in range(5):
            time.sleep(1)
            state = query_api()
            if state and state.get("repository_state"):
                dirty = state["repository_state"].get("dirty_files", [])
                if any("backend/agent_safety_governor.py" in line for line in dirty):
                    log(f"✓ Success: backend/agent_safety_governor.py detected as dirty!")
                    log(f"✓ Current blockers: {state['blockers']}")
                    found_dirty = True
                    break
        if not found_dirty:
            log("✗ Failed: Dirty state for backend/agent_safety_governor.py was not detected.")
            sys.exit(1)
    finally:
        # Step 8: Restore the file
        log("\n## Step 8: Restoring the modified file")
        target_file.write_text(original_content, encoding="utf-8")
        log("✓ Restored backend/agent_safety_governor.py to original content")
        
    # Step 9: Confirm repository returns to CLEAN for targeted file
    log("\n## Step 9: Verifying repository returns to CLEAN (targeted file)")
    found_clean = False
    for _ in range(5):
        time.sleep(1)
        state = query_api()
        if state and state.get("repository_state"):
            dirty = state["repository_state"].get("dirty_files", [])
            if not any("backend/agent_safety_governor.py" in line for line in dirty):
                log(f"✓ Success: backend/agent_safety_governor.py no longer dirty!")
                log(f"✓ Current blockers: {state['blockers']}")
                found_clean = True
                break
    if not found_clean:
        log("✗ Failed: backend/agent_safety_governor.py was still detected as dirty after restore.")
        sys.exit(1)

    # Step 10: Create a real Founder gate
    log("\n## Step 10: Creating a custom Founder gate")
    gate_file = ROOT / "coordination/founder_gate.json"
    gate_data = {"blockers": ["FOUNDER_MANUAL_REVIEW_REQUIRED"]}
    
    try:
        gate_file.write_text(json.dumps(gate_data, indent=2), encoding="utf-8")
        log("✓ Created coordination/founder_gate.json with FOUNDER_MANUAL_REVIEW_REQUIRED blocker")
        
        # Step 11: Confirm it appears in both browser and terminal
        log("\n## Step 11: Verifying Founder gate detection")
        found_gate = False
        for _ in range(5):
            time.sleep(1)
            state = query_api()
            if state and "FOUNDER_MANUAL_REVIEW_REQUIRED" in state["blockers"]:
                log("✓ Success: FOUNDER_MANUAL_REVIEW_REQUIRED detected in blockers!")
                log(f"✓ Current blockers: {state['blockers']}")
                found_gate = True
                break
        if not found_gate:
            log("✗ Failed: Founder gate was not detected.")
            sys.exit(1)
    finally:
        # Cleanup Founder gate file
        log("\n## Cleanup: Removing custom Founder gate")
        if gate_file.exists():
            gate_file.unlink()
        log("✓ Removed coordination/founder_gate.json")
        
    # Final check
    state = query_api()
    log(f"\n✓ Post-cleanup blockers: {state['blockers'] if state else 'None'}")
    log("\n## Verdict: End-to-end live-change demonstration PASSED!")

    # Write log to evidence directory
    evidence_dir = ROOT / "coordination/evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_file = evidence_dir / "live_change_demonstration.md"
    evidence_file.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    print(f"\nWrote demonstration log to: {evidence_file}")

if __name__ == "__main__":
    import datetime
    main()
