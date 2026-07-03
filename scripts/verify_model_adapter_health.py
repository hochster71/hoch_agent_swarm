#!/usr/bin/env python3
import json
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "has_live_project_tracker/data"

def check_remote_probe():
    # Execute probe directly on HOCH-200 to verify actual endpoint behavior
    res = subprocess.run(
        "ssh root@50.116.41.183 'curl -s -o /dev/null -w \"%{http_code}\" http://localhost:1234/v1/models'",
        shell=True, capture_output=True, text=True
    )
    return res.stdout.strip() == "200"

def main():
    print("Executing Model Adapter Health Verification Gate...")
    
    # 1. Check registry
    registry_file = DATA_DIR / "helm_adapter_registry.json"
    if not registry_file.exists():
        print("❌ Verification failed: helm_adapter_registry.json does not exist.")
        sys.exit(1)
        
    with open(registry_file, "r") as f:
        adapters = json.load(f)
        
    lmstudio = adapters.get("lmstudio", {})
    registered_status = lmstudio.get("status", "DEGRADED")
    
    # 2. Check remote probe
    probe_ok = check_remote_probe()
    expected_status = "ONLINE" if probe_ok else "DEGRADED"
    
    if registered_status != expected_status:
        print(f"❌ Verification failed: Stale adapter status in registry. Registered: {registered_status}, Actual Probe: {expected_status}")
        sys.exit(1)
        
    print(f"🟢 Registered status ({registered_status}) matches actual probe status ({expected_status}).")
    
    # 3. Check dependency doc
    doc_path = ROOT / "docs/evidence/runtime_scenarios/20260702T222129Z-24-7-autonomy-reset/model-adapter-dependency.md"
    if not doc_path.exists() or doc_path.stat().st_size == 0:
        print("❌ Verification failed: docs/evidence/runtime_scenarios/20260702T222129Z-24-7-autonomy-reset/model-adapter-dependency.md is missing or empty.")
        sys.exit(1)
        
    print("🟢 Model adapter dependency documentation is verified.")
    print("✅ Model Adapter Health verification PASSED.")

if __name__ == "__main__":
    main()
