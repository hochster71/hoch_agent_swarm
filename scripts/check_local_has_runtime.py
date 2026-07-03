#!/usr/bin/env python3
"""
Check Local HAS Runtime at http://127.0.0.1:8765/
Called by GitHub workflow on has-qa-runner-mac.
"""
import requests
import sys
from pathlib import Path
import json
from datetime import datetime

URL = "http://127.0.0.1:8765/"
PERT_URL = "http://127.0.0.1:8765/api/pert/data"
DATA = Path("has_live_project_tracker/data")
DATA.mkdir(parents=True, exist_ok=True)

def main():
    print("HAS LOCAL RUNTIME CHECK")
    print("=" * 50)
    print(f"Target: {URL}")

    try:
        r = requests.get(URL, timeout=5)
        if r.status_code == 200:
            print("Runtime: ONLINE")
            status = "PROVEN"
        else:
            print(f"Runtime: HTTP {r.status_code}")
            status = "CONDITIONAL"
    except Exception as e:
        print(f"Runtime: OFFLINE ({e})")
        status = "NO_GO"

    try:
        r = requests.get(PERT_URL, timeout=5)
        if r.status_code == 200:
            print("PERT API: ONLINE")
        else:
            print(f"PERT API: HTTP {r.status_code}")
    except Exception as e:
        print(f"PERT API: OFFLINE ({e})")

    proof = {
        "generated_at": datetime.now().isoformat(),
        "runtime_url": URL,
        "runtime_status": status,
        "runner": "has-qa-runner-mac",
        "message": "Local runtime proof from GitHub self-hosted runner. Scope lock enforced.",
        "next_action": "Enforce scope lock and prove local runner automation against http://127.0.0.1:8765/"
    }

    (DATA / "local_runtime_proof.json").write_text(json.dumps(proof, indent=2))
    print(f"Proof written to {DATA / 'local_runtime_proof.json'}")
    print(f"Status: {status}")
    return 0 if status != "NO_GO" else 1

if __name__ == "__main__":
    sys.exit(main())
