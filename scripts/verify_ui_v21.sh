#!/usr/bin/env bash
set -euo pipefail

cd /Users/michaelhoch/hoch_agent_swarm

echo "=== VERIFY UI V2.1 ROUTE ==="
curl -fsS http://127.0.0.1:8765/ui-v2 > /tmp/has_ui_v21.html

grep -q "Operator Console V2.1" /tmp/has_ui_v21.html
grep -q 'data-tab="command"' /tmp/has_ui_v21.html
grep -q 'data-tab="pods"' /tmp/has_ui_v21.html
grep -q 'data-tab="revenue"' /tmp/has_ui_v21.html
grep -q 'data-tab="evidence"' /tmp/has_ui_v21.html
grep -q 'data-tab="pert"' /tmp/has_ui_v21.html
grep -q 'data-tab="watchdog"' /tmp/has_ui_v21.html

echo "UI_V21_ROUTE: PASS"

echo
echo "=== VERIFY API JSON ==="
curl -fsS http://127.0.0.1:8765/api/pert/data > /tmp/has_api_pert_data.json

python3 -m json.tool /tmp/has_api_pert_data.json > /tmp/has_api_pert_data.pretty.json

echo "API_JSON: PASS"

echo
echo "=== VERIFY CRITICAL TELEMETRY ==="
python3 - /tmp/has_api_pert_data.json <<'PY'
import json
import sys
from pathlib import Path

api_path = Path(sys.argv[1])
data = json.loads(api_path.read_text())

src = data.get("freshness_authority", {}).get("reconciled_sources", {})
critical = ["global_verify", "hoch_pods_runtime_state", "hoch_pod_schedule"]

failed = []
for k in critical:
    s = src.get(k, {})
    state = s.get("computed_state")
    age = s.get("freshness_age_seconds")
    reason = s.get("reason")
    print(f"{k}: {state} age={age} reason={reason}")
    if state != "FRESH":
        failed.append(k)

if failed:
    raise SystemExit(f"CRITICAL_TELEMETRY: FAIL {failed}")

print("CRITICAL_TELEMETRY: PASS")
PY

echo
echo
echo "=== VERIFY WATCHDOG ==="
if [ "${WATCHDOG_REQUIRED:-1}" = "0" ]; then
  echo "WATCHDOG: SKIP release hygiene mode"
else
  if [ -f logs/has_telemetry_watchdog.pid ]; then
    PID="$(cat logs/has_telemetry_watchdog.pid)"
    if ps -p "$PID" >/dev/null 2>&1; then
      echo "WATCHDOG: PASS pid=$PID"
    else
      echo "WATCHDOG: FAIL pid=$PID not running"
      exit 1
    fi
  else
    echo "WATCHDOG: FAIL missing pid file"
    exit 1
  fi
fi

echo "UI_V21_SMOKE: PASS"
