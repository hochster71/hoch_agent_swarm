#!/usr/bin/env bash
# scripts/rc41_worker_telemetry_accuracy_verify.sh
# Verification runner for RC41 Worker Telemetry Accuracy.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=================================================="
echo "RUNNING RC41 WORKER TELEMETRY ACCURACY VERIFICATION"
echo "=================================================="

# Activate virtualenv if present
if [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

cd "$PROJECT_ROOT"

# Check 1: Trigger relay health probe
echo "Running Check 1: Triggering relay health probe..."
bash scripts/relay_health_probe.sh
echo "  [PASS] Relay health probe evidence written."

# Check 2: Run accuracy checklist audit
echo "Running Check 2: Running worker telemetry accuracy check..."
bash scripts/worker_telemetry_accuracy_check.sh
echo "  [PASS] Telemetry check succeeded."

# Check 3: Check that public port 3012 is closed
echo "Running Check 3: Public port 3012 safety check..."
if python3 -c "import socket; s = socket.socket(); s.settimeout(3); s.connect(('50.116.41.183', 3012))" 2>/dev/null; then
    echo "  [FAIL] Public port 3012 is reachable!"
    exit 1
else
    echo "  [PASS] Public port 3012 remains securely closed."
fi

# Check 4: Run E2E Playwright spec
echo "Running Check 4: Running Playwright E2E tests..."
npx playwright test tests/e2e/rc41-worker-telemetry-accuracy.spec.ts --reporter=list
echo "  [PASS] Playwright E2E tests passed."

echo "=================================================="
echo ">> SUCCESS: All RC41 Worker Telemetry Accuracy checks PASS!"
echo "=================================================="
