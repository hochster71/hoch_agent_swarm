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

def check_model_endpoint():
    import http.client
    try:
        conn = http.client.HTTPConnection("localhost", 1234, timeout=2)
        conn.request("GET", "/v1/models")
        res = conn.getresponse()
        if res.status == 200:
            return "ONLINE"
    except:
        pass
    return "DEGRADED"

def check_service(service_name):
    try:
        res = subprocess.run(f"systemctl is-active {service_name}", shell=True, capture_output=True, text=True)
        return "ONLINE" if res.stdout.strip() == "active" else "OFFLINE"
    except:
        return "OFFLINE"

def main():
    print(f"[{get_current_utc()}] HAS Runtime Watchdog started.")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Initialize files if missing
    adapter_file = DATA_DIR / "helm_adapter_registry.json"
    helm_state_file = DATA_DIR / "helm_runtime_state.json"
    
    while True:
        try:
            services = {
                "helm-runner": check_service("helm-runner"),
                "has-agent-dispatcher": check_service("has-agent-dispatcher"),
                "hasf-product-factory": check_service("hasf-product-factory")
            }
            
            # Model endpoint truth check
            model_status = check_model_endpoint()
            
            # Update adapter registry
            if adapter_file.exists():
                with open(adapter_file, "r") as f:
                    try:
                        adapters = json.load(f)
                    except:
                        adapters = {}
                if "lmstudio" in adapters:
                    adapters["lmstudio"]["status"] = model_status
                    adapters["lmstudio"]["last_checked"] = get_current_utc()
                    with open(adapter_file, "w") as f:
                        json.dump(adapters, f, indent=2)
            
            # Update helm runtime state
            helm_state = {}
            if helm_state_file.exists():
                with open(helm_state_file, "r") as f:
                    try:
                        helm_state = json.load(f)
                    except:
                        pass
            helm_state["adapter_status"] = model_status
            helm_state["last_checked"] = get_current_utc()
            with open(helm_state_file, "w") as f:
                json.dump(helm_state, f, indent=2)
            
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
                          "services": services,
                          "model_endpoint_status": model_status
                        }
                    }
                }, f, indent=2)
                
        except Exception as e:
            print(f"Error in watchdog: {e}")
            
        time.sleep(10)

if __name__ == "__main__":
    main()
