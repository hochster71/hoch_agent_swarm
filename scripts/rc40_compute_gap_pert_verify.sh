#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=================================================="
echo "RUNNING RC40 COMPUTE UTILIZATION GAP VERIFICATION"
echo "=================================================="

# Activate virtualenv if present
if [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

cd "$PROJECT_ROOT"

# Check 1: Run Compute Gap Analysis to populate metrics
echo "Running Check 1: Compute Gap Analysis refresh..."
bash scripts/compute_gap_analysis.sh
echo "  [PASS] Compute Gap Analysis refreshed successfully."

# Check 2: Run Telemetry Truth Compliance Audit
echo "Running Check 2: Telemetry Truth compliance audit..."
bash scripts/telemetry_truth_check.sh
echo "  [PASS] Telemetry Truth compliance audit passed."

# Check 3: Run Playwright E2E Compute Gap & PERT Recalibration test
echo "Running Check 3: Playwright E2E Compute Gap & PERT Recalibration test..."
E2E_BASE_URL=http://127.0.0.1:8765 npx playwright test tests/e2e/rc40-compute-gap-pert.spec.ts --reporter=list
echo "  [PASS] Playwright E2E test passed."

# Check 4: Confirm public port 3012 remains closed
echo "Running Check 4: Port 3012 Public Exposure Check..."
python3 -c "import socket
s = socket.socket()
s.settimeout(2.0)
try:
    s.connect(('50.116.41.183', 3012))
    print('  [FAIL] Port 3012 is open!')
    exit(1)
except Exception:
    print('  [PASS] Port 3012 is closed.')
"
echo "  [PASS] Public port 3012 is closed."

echo "=================================================="
echo ">> SUCCESS: All RC40 Compute Gap & PERT checks PASS!"
echo "=================================================="
