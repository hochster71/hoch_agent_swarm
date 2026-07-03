#!/usr/bin/env python3
import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "has_live_project_tracker/data"

def parse_utc(ts_str):
    if not ts_str:
        return None
    try:
        # Standardize formats
        ts_str = ts_str.replace("Z", "")
        return datetime.fromisoformat(ts_str)
    except:
        return None

def check_freshness():
    # 1. Load files
    state_file = DATA_DIR / "helm_runtime_state.json"
    watchdog_file = DATA_DIR / "has_runtime_state.json"
    queue_file = DATA_DIR / "helm_task_queue.json"
    adapter_file = DATA_DIR / "helm_adapter_registry.json"

    # Malformed check
    for f in [state_file, watchdog_file, queue_file, adapter_file]:
        if not f.exists():
            print(f"❌ Missing file: {f.name}")
            sys.exit(1)
        try:
            with open(f, "r") as fh:
                json.load(fh)
        except Exception as e:
            print(f"❌ Malformed JSON in {f.name}: {e}")
            sys.exit(1)

    with open(state_file, "r") as fh:
        helm_state = json.load(fh)
    with open(watchdog_file, "r") as fh:
        watchdog_state = json.load(fh)
    with open(queue_file, "r") as fh:
        queue = json.load(fh)
    with open(adapter_file, "r") as fh:
        adapters = json.load(fh)

    now = datetime.utcnow()

    # 2. HELM heartbeat
    helm_check_time = parse_utc(helm_state.get("last_checked"))
    if not helm_check_time:
        print("❌ Stale/missing HELM heartbeat timestamp")
        sys.exit(1)
    helm_age = (now - helm_check_time).total_seconds()
    if helm_age > 60:
        print(f"❌ HELM heartbeat is stale ({helm_age:.1f}s > 60s)")
        sys.exit(1)

    # 3. Watchdog heartbeat
    watchdog_check_time = parse_utc(watchdog_state.get("last_heartbeat"))
    if not watchdog_check_time:
        print("❌ Stale/missing Watchdog heartbeat timestamp")
        sys.exit(1)
    watchdog_age = (now - watchdog_check_time).total_seconds()
    if watchdog_age > 30:
        print(f"❌ Watchdog heartbeat is stale ({watchdog_age:.1f}s > 30s)")
        sys.exit(1)

    # 4. Adapter probe
    for name, adapter in adapters.items():
        adapter_check = parse_utc(adapter.get("last_checked"))
        if not adapter_check:
            print(f"❌ Missing check timestamp for adapter {name}")
            sys.exit(1)
        adapter_age = (now - adapter_check).total_seconds()
        if adapter_age > 30:
            print(f"❌ Adapter probe for {name} is stale ({adapter_age:.1f}s > 30s)")
            sys.exit(1)

    # 5. Active task state stale
    active_task_id = helm_state.get("active_task_id")
    if active_task_id:
        # Find active task in queue
        matching = [t for t in queue if t["id"] == active_task_id]
        if matching:
            task = matching[0]
            created_time = parse_utc(task.get("created_at"))
            if created_time:
                task_age = (now - created_time).total_seconds()
                if task_age > 300: # 5 minutes
                    print(f"❌ Active task {active_task_id} has been running/stale for too long ({task_age:.1f}s > 300s)")
                    sys.exit(1)

    # 6. Completed task evidence validation
    for task in queue:
        if task.get("status") == "completed":
            result = task.get("result")
            if not result:
                print(f"❌ Completed task {task['id']} lacks evidence reference")
                sys.exit(1)
            # Verify evidence file exists
            ev_str = result.replace("file://", "")
            if sys.platform == "darwin":
                ev_str = ev_str.replace("/root/hoch_agent_swarm/", "/Users/michaelhoch/hoch_agent_swarm/")
            ev_path = Path(ev_str)
            if not ev_path.exists():
                print(f"❌ Evidence file for {task['id']} does not exist at {ev_path}")
                sys.exit(1)
            
            # Check completed_at time
            completed_time = parse_utc(task.get("completed_at"))
            # Get evidence file modified time or parsed content time
            # We'll use file modified time for validation
            ev_mtime = datetime.utcfromtimestamp(ev_path.stat().st_mtime)
            if ev_mtime < completed_time:
                # Allow minor sub-second/second diffs
                if (completed_time - ev_mtime).total_seconds() > 5:
                    print(f"❌ Evidence file for {task['id']} is older than task completion time")
                    sys.exit(1)

    print("🟢 All runtime truth freshness checks PASSED.")

if __name__ == "__main__":
    check_freshness()
