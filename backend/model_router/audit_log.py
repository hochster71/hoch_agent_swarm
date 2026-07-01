import os
import json
import time
from pathlib import Path

AUDIT_DIR = Path(__file__).parent.parent.parent / "audit"
AUDIT_FILE = AUDIT_DIR / "model_routing.jsonl"

def log_routing_event(event_type: str, payload: dict) -> bool:
    try:
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        
        log_entry = {
            "timestamp": time.time(),
            "event_type": event_type,
            **payload
        }
        
        with open(AUDIT_FILE, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        return True
    except Exception as e:
        print(f"Failed to write model routing audit log: {e}")
        return False

def get_audit_logs(limit: int = 50) -> list:
    if not AUDIT_FILE.exists():
        return []
    
    try:
        logs = []
        with open(AUDIT_FILE, "r") as f:
            for line in f:
                if line.strip():
                    logs.append(json.loads(line.strip()))
        return logs[-limit:]
    except Exception as e:
        print(f"Failed to read model routing audit logs: {e}")
        return []
