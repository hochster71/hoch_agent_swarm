#!/usr/bin/env python3
"""HELM Full Verification Harness.

Executes all active verification scripts present in the repository.
"""
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def main():
    print("=== HELM Full Verification Run ===")
    
    scripts = [
        "scripts/verify_ag_execution_burn_in.py",
        "scripts/verify_ag_execution_fencing.py",
        "scripts/verify_ag_execution_proofs.py",
        "scripts/verify_ag_execution_queue.py",
        "scripts/verify_helm_autonomy_layer.py",
        "scripts/verify_helm_orchestration_bridge.py",
    ]
    
    all_ok = True
    for script in scripts:
        script_path = ROOT / script
        if not script_path.exists():
            print(f"[-] Skip {script} (does not exist)")
            continue
            
        print(f"[*] Running {script}...")
        try:
            out = subprocess.check_output([sys.executable, str(script_path)], text=True, stderr=subprocess.STDOUT)
            print(out)
            print(f"[+] {script} PASSED")
        except subprocess.CalledProcessError as e:
            print(e.output)
            print(f"[x] {script} FAILED (exit code: {e.returncode})")
            all_ok = False
            
    if not all_ok:
        sys.exit(1)
        
    print("[+] All verification scripts passed successfully.")

if __name__ == "__main__":
    main()
