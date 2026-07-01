#!/usr/bin/env python3
import sys
import subprocess
import os

def check_drift():
    print("[verify_no_drift] Executing current-state drift check...")
    res = subprocess.run(["npm", "run", "qa:production-no-drift-current-state"], capture_output=True, text=True)
    if res.returncode != 0:
        print("[verify_no_drift] FAIL: Drift or missing files detected!")
        print(res.stdout)
        print(res.stderr)
        
        # Write a local report
        report_dir = "artifacts/orchestrator/reports"
        os.makedirs(report_dir, exist_ok=True)
        report_path = os.path.join(report_dir, "drift_failure_report.json")
        with open(report_path, "w") as f:
            f.write(f'{{\n  "status": "FAIL",\n  "error": "Drift detected",\n  "stdout": {repr(res.stdout)}\n}}\n')
        
        sys.exit(1)
    print("[verify_no_drift] PASS: Zero drift detected.")
    return True

if __name__ == "__main__":
    check_drift()
