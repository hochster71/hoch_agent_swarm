#!/usr/bin/env python3
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "has_live_project_tracker" / "data"
DATA.mkdir(parents=True, exist_ok=True)

commands = [
    ["python3", "scripts/generate_global_verify.py"],
    ["python3", "scripts/generate_hoch_pods_runtime_state.py"],
    ["python3", "scripts/normalize_hoch_pods_runtime_state.py"],
    ["python3", "scripts/generate_hoch_pod_schedule.py"],
    ["python3", "scripts/verify_live_telemetry_freshness.py"],
]

results = []
overall = "PASS"

for cmd in commands:
    path = ROOT / cmd[1]
    if not path.exists():
        overall = "FAIL"
        results.append({
            "command": " ".join(cmd),
            "ok": False,
            "returncode": None,
            "error": f"missing script {cmd[1]}",
        })
        continue

    try:
        completed = subprocess.run(
            cmd,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=120,
        )
        ok = completed.returncode == 0
        if not ok:
            overall = "FAIL"

        results.append({
            "command": " ".join(cmd),
            "ok": ok,
            "returncode": completed.returncode,
            "stdout_tail": completed.stdout[-2000:],
            "stderr_tail": completed.stderr[-2000:],
        })
    except Exception as exc:
        overall = "FAIL"
        results.append({
            "command": " ".join(cmd),
            "ok": False,
            "returncode": None,
            "error": str(exc),
        })

payload = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "status": overall,
    "results": results,
    "single_next_action": "Reload http://127.0.0.1:8765/ and confirm quarantine is cleared." if overall == "PASS" else "Inspect failed telemetry producer command.",
}

(DATA / "live_telemetry_refresh_result.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

print(f"LIVE_TELEMETRY_REFRESH: {overall}")

if overall != "PASS":
    print(json.dumps(payload, indent=2))
    sys.exit(1)
