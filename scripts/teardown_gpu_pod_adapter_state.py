#!/usr/bin/env python3
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = ROOT / "has_live_project_tracker/data/gpu_pod_adapter_state.json"
REGISTRY_FILE = ROOT / "has_live_project_tracker/data/helm_adapter_registry.json"

def teardown():
    print("Initiating GPU Pod Adapter Teardown...")
    
    # 1. Update state file to REMOVED
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
        state["status"] = "REMOVED"
        state["promoted_to_tier_3"] = False
        state["endpoint"] = "none"
        state["models_loaded"] = []
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
            
    # 2. Set registry status to OFFLINE
    if REGISTRY_FILE.exists():
        with open(REGISTRY_FILE, "r") as f:
            registry = json.load(f)
        if "ollama_gpu_pod" in registry:
            registry["ollama_gpu_pod"]["status"] = "OFFLINE"
            registry["ollama_gpu_pod"]["base_url"] = "none"
        with open(REGISTRY_FILE, "w") as f:
            json.dump(registry, f, indent=2)
            
    print("🟢 GPU Pod teardown completed safely. Control plane remains online.")

if __name__ == "__main__":
    teardown()
