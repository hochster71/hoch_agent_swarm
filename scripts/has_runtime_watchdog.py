#!/usr/bin/env python3
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "has_live_project_tracker/data"
HAS_STATE_FILE = DATA_DIR / "has_runtime_state.json"

def get_current_utc():
    return datetime.utcnow().isoformat() + "Z"

def check_service(service_name):
    try:
        res = subprocess.run(f"systemctl is-active {service_name}", shell=True, capture_output=True, text=True)
        return "ONLINE" if res.stdout.strip() == "active" else "OFFLINE"
    except:
        return "OFFLINE"

def main():
    print(f"[{get_current_utc()}] HAS Runtime Watchdog started.")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    while True:
        try:
            services = {
                "helm-runner": check_service("helm-runner"),
                "has-agent-dispatcher": check_service("has-agent-dispatcher"),
                "hasf-product-factory": check_service("hasf-product-factory")
            }
            
            with open(HAS_STATE_FILE, "w") as f:
                json.dump({
                    "status": "ONLINE",
                    "uptime_seconds": int(time.time()),
                    "last_heartbeat": get_current_utc(),
                    "active_services": [name for name, status in services.items() if status == "ONLINE"],
                    "monitored_nodes": {
                        "HOCH-200": {
                          "ip": "50.116.41.183",
                          "status": "ONLINE",
                          "services": services
                        }
                    }
                }, f, indent=2)
                
        except Exception as e:
            print(f"Error in watchdog: {e}")
            
        time.sleep(10)

if __name__ == "__main__":
    main()
