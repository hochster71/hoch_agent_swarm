#!/usr/bin/env python3
import json
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "has_live_project_tracker/data"

def refresh():
    now_str = datetime.datetime.utcnow().isoformat() + "Z"
    
    # 1. helm_runtime_state.json
    state_file = DATA_DIR / "helm_runtime_state.json"
    if state_file.exists():
        with open(state_file, "r") as f:
            data = json.load(f)
        data["last_checked"] = now_str
        with open(state_file, "w") as f:
            json.dump(data, f, indent=2)
            
    # 2. has_runtime_state.json
    watchdog_file = DATA_DIR / "has_runtime_state.json"
    if watchdog_file.exists():
        with open(watchdog_file, "r") as f:
            data = json.load(f)
        data["last_heartbeat"] = now_str
        with open(watchdog_file, "w") as f:
            json.dump(data, f, indent=2)
            
    # 3. helm_adapter_registry.json
    adapter_file = DATA_DIR / "helm_adapter_registry.json"
    if adapter_file.exists():
        with open(adapter_file, "r") as f:
            data = json.load(f)
        for name in data:
            data[name]["last_checked"] = now_str
        with open(adapter_file, "w") as f:
            json.dump(data, f, indent=2)
            
    # 4. gpu_pod_adapter_state.json
    gpu_state_file = DATA_DIR / "gpu_pod_adapter_state.json"
    if gpu_state_file.exists():
        with open(gpu_state_file, "r") as f:
            data = json.load(f)
        data["updated_at"] = now_str
        with open(gpu_state_file, "w") as f:
            json.dump(data, f, indent=2)
            
    print(f"🟢 Refreshed all heartbeats to {now_str}")

if __name__ == "__main__":
    refresh()
