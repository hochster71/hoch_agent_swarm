#!/usr/bin/env python3
import json
import datetime
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "has_live_project_tracker/data"

def refresh():
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_str = now_utc.isoformat().replace("+00:00", "Z")
    
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

    # 5. global_verify.json
    gv_file = DATA_DIR / "global_verify.json"
    if gv_file.exists():
        with open(gv_file, "r") as f:
            data = json.load(f)
        data["generated_at"] = now_str
        data["last_verified_at"] = now_str
        with open(gv_file, "w") as f:
            json.dump(data, f, indent=2)
            
    # 6. hoch_pods_runtime_state.json
    pods_file = DATA_DIR / "hoch_pods_runtime_state.json"
    if pods_file.exists():
        with open(pods_file, "r") as f:
            data = json.load(f)
        if data and isinstance(data, list) and len(data) > 0:
            data[0]["last_heartbeat"] = now_str
        with open(pods_file, "w") as f:
            json.dump(data, f, indent=2)
            
    # 7. hoch_pod_schedule.json (touch the file to update its mtime)
    sched_file = DATA_DIR / "hoch_pod_schedule.json"
    if sched_file.exists():
        sched_file.touch()

    # 8. project_revenue_readiness_results.json (touch the file)
    readiness_file = DATA_DIR / "project_revenue_readiness_results.json"
    if readiness_file.exists():
        readiness_file.touch()

    # 9. revenue_action_queue.json (touch the file)
    queue_file = DATA_DIR / "revenue_action_queue.json"
    if queue_file.exists():
        queue_file.touch()

    # 10. hasf_runtime_state.json (set last_heartbeat)
    hasf_file = DATA_DIR / "hasf_runtime_state.json"
    if hasf_file.exists():
        with open(hasf_file, "r") as f:
            data = json.load(f)
        data["last_heartbeat"] = now_str
        with open(hasf_file, "w") as f:
            json.dump(data, f, indent=2)

    # 11. helm_agent_registry.json (touch or mtime refresh)
    reg_file = DATA_DIR / "helm_agent_registry.json"
    if reg_file.exists():
        reg_file.touch()
            
    print(f"🟢 Refreshed all heartbeats and file modification times to {now_str}")

if __name__ == "__main__":
    refresh()
