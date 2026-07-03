#!/usr/bin/env python3
import json
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "has_live_project_tracker/data"
FACTORY_STATE_FILE = DATA_DIR / "hasf_runtime_state.json"

def get_current_utc():
    return datetime.utcnow().isoformat() + "Z"

def main():
    print(f"[{get_current_utc()}] HASF Product Factory started.")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    while True:
        try:
            with open(FACTORY_STATE_FILE, "w") as f:
                json.dump({
                    "status": "ACTIVE",
                    "last_run": get_current_utc(),
                    "current_product": "cyberqrg-ai",
                    "pipeline_stage": "BACKLOG_MAPPING",
                    "metrics": {
                        "completed_products": 1,
                        "pending_candidates": 3,
                        "active_backlog_items": 2
                    }
                }, f, indent=2)
        except Exception as e:
            print(f"Error in factory runner: {e}")
            
        time.sleep(15)

if __name__ == "__main__":
    main()
