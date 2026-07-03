#!/usr/bin/env python3
import json
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "has_live_project_tracker/data"

def check_remote_lmstudio_probe():
    res = subprocess.run(
        "ssh root@50.116.41.183 'curl -s -o /dev/null -w \"%{http_code}\" http://localhost:1234/v1/models'",
        shell=True, capture_output=True, text=True
    )
    return res.stdout.strip() == "200"

def check_remote_ollama_probe():
    res = subprocess.run(
        "ssh root@50.116.41.183 'curl -s -o /dev/null -w \"%{http_code}\" http://localhost:11434/api/tags'",
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
        
    # Check LM Studio status
    lmstudio = adapters.get("lmstudio", {})
    registered_lmstudio_status = lmstudio.get("status", "DEGRADED")
    lmstudio_probe_ok = check_remote_lmstudio_probe()
    expected_lmstudio_status = "ONLINE" if lmstudio_probe_ok else "DEGRADED"
    
    if registered_lmstudio_status != expected_lmstudio_status:
        print(f"❌ Verification failed: Stale lmstudio status in registry. Registered: {registered_lmstudio_status}, Actual Probe: {expected_lmstudio_status}")
        sys.exit(1)
    print(f"🟢 Registered lmstudio status ({registered_lmstudio_status}) matches actual probe status ({expected_lmstudio_status}).")
    
    # Check Ollama Native status
    ollama = adapters.get("ollama_native", {})
    registered_ollama_status = ollama.get("status", "DEGRADED")
    ollama_probe_ok = check_remote_ollama_probe()
    expected_ollama_status = "ONLINE" if ollama_probe_ok else "DEGRADED"
    
    if registered_ollama_status != expected_ollama_status:
        print(f"❌ Verification failed: Stale ollama_native status in registry. Registered: {registered_ollama_status}, Actual Probe: {expected_ollama_status}")
        sys.exit(1)
    print(f"🟢 Registered ollama_native status ({registered_ollama_status}) matches actual probe status ({expected_ollama_status}).")
    
    # 3. Check dependency doc
    doc_path = ROOT / "docs/evidence/runtime_scenarios/20260702T222129Z-24-7-autonomy-reset/model-adapter-dependency.md"
    if not doc_path.exists() or doc_path.stat().st_size == 0:
        print("❌ Verification failed: docs/evidence/runtime_scenarios/20260702T222129Z-24-7-autonomy-reset/model-adapter-dependency.md is missing or empty.")
        sys.exit(1)
        
    print("🟢 Model adapter dependency documentation is verified.")
    print("✅ Model Adapter Health verification PASSED.")

if __name__ == "__main__":
    main()
