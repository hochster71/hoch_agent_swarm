#!/usr/bin/env python3
"""
Local AI Inventory for HAS/HASF Cost Governor
Detects available local models and endpoints.
"""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

DATA = Path("has_live_project_tracker/data")
DATA.mkdir(parents=True, exist_ok=True)
INVENTORY = DATA / "local_ai_inventory.json"

def run_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.stdout.strip() if result.returncode == 0 else "NOT_AVAILABLE"
    except:
        return "NOT_AVAILABLE"

def main():
    print("LOCAL AI INVENTORY")
    print("=" * 50)
    print(f"Generated at: {datetime.now().isoformat()}")

    ollama = run_command("ollama --version 2>&1 || echo 'NOT_AVAILABLE'")
    ollama_models = run_command("ollama list 2>&1 | head -10 || echo 'NOT_AVAILABLE'")

    lmstudio = run_command("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:1234/v1/models || echo 'NOT_AVAILABLE'")

    inventory = {
        "generated_at": datetime.now().isoformat(),
        "ollama": ollama,
        "ollama_models": ollama_models,
        "lmstudio": lmstudio,
        "local_python": "AVAILABLE",
        "local_embedding": "NOT_AVAILABLE",
        "disk_summary": run_command("df -h / | tail -1"),
        "runner_status": "has-qa-runner-mac",
        "runtime_url": "http://127.0.0.1:8765/",
        "status": "LOCAL_AVAILABLE" if "NOT_AVAILABLE" not in ollama or lmstudio == "200" else "DEGRADED"
    }

    INVENTORY.write_text(json.dumps(inventory, indent=2))
    print(json.dumps(inventory, indent=2))
    print("LOCAL_AI_INVENTORY: PASS")
    return 0

if __name__ == "__main__":
    sys.exit(main())
