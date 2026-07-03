#!/usr/bin/env python3
import json
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "has_live_project_tracker/data"
DISPATCHER_STATE_FILE = DATA_DIR / "has_agent_dispatcher_state.json"
AGENT_REGISTRY_FILE = DATA_DIR / "helm_agent_registry.json"

def get_current_utc():
    return datetime.utcnow().isoformat() + "Z"

def main():
    print(f"[{get_current_utc()}] HAS Agent Dispatcher started.")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    while True:
        try:
            # Refresh registry status
            registry = {}
            if AGENT_REGISTRY_FILE.exists():
                with open(AGENT_REGISTRY_FILE, "r") as f:
                    registry = json.load(f)
                    
            # Set all agents to active/online
            for name, profile in registry.items():
                profile["status"] = "READY"
                profile["last_heartbeat"] = get_current_utc()
                
            with open(AGENT_REGISTRY_FILE, "w") as f:
                json.dump(registry, f, indent=2)
                
            # Write dispatcher metadata
            with open(DISPATCHER_STATE_FILE, "w") as f:
                json.dump({
                    "status": "ONLINE",
                    "last_tick": get_current_utc(),
                    "registered_agents": list(registry.keys())
                }, f, indent=2)
                
        except Exception as e:
            print(f"Error in dispatcher: {e}")
            
        time.sleep(10)

if __name__ == "__main__":
    main()
