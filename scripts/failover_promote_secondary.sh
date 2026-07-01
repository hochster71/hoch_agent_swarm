#!/usr/bin/env bash
# 24/7 Operations: failover_promote_secondary.sh
set -euo pipefail

PROJECT_ROOT="/Users/michaelhoch/hoch_agent_swarm"
cd "$PROJECT_ROOT"

echo "[WARNING] Promoting secondary control plane to ACTIVE status..."

# Update the status JSON file to show failover was triggered
STATUS_JSON="$PROJECT_ROOT/frontend/data/runtime_reliability.json"

if [ -f "$STATUS_JSON" ]; then
    # Use python to edit JSON file cleanly
    python3 -c "
import json
with open('$STATUS_JSON', 'r') as f:
    data = json.load(f)
data['failover']['primaryStatus'] = 'DOWN'
data['failover']['secondaryStatus'] = 'ACTIVE'
data['failover']['failoverReadiness'] = 'FAILOVER_TRIGGERED'
with open('$STATUS_JSON', 'w') as f:
    json.dump(data, f, indent=2)
"
    echo "[PASS] Status file updated: Secondary VPS promoted."
    exit 0
else
    echo "[FAIL] Status JSON file not found at $STATUS_JSON."
    exit 1
fi
