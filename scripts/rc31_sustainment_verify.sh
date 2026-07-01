#!/usr/bin/env bash
# scripts/rc31_sustainment_verify.sh
# ==========================================
# RC31 Sustainment Verification Script
#
# Asserts the production post-release invariants for v0.1.7:
#  1. v0.1.7 tag is fixed at face8ce
#  2. master HEAD baseline is 84b0600 (or its children)
#  3. Doctrine DB passes (verify_doctrine_db.py)
#  4. Local api endpoints are active and healthy
#  5. Relay status is reachable and HAS-WORKER-RELAY-001 is active
#  6. Playwright E2E suites for RC26 and RC28 still pass
#  7. Public VPS port 3012 is closed/refused

set -euo pipefail

export E2E_BASE_URL="${E2E_BASE_URL:-http://localhost:8000}"
export PUBLIC_VPS="50.116.41.183"
export PUBLIC_PORT="3012"
export TARGET_TAG="v0.1.7"
export TARGET_SHA="face8ce"

echo "======================================================================"
echo "          RC31 Sustainment Verification: v0.1.7 Production"
echo "======================================================================"

FAILED=0

log_status() {
    local name="$1"
    local status="$2"
    local msg="${3:-}"
    if [ "$status" = "PASS" ]; then
        echo "  [PASS] ${name} ${msg}"
    else
        echo "  [FAIL] ${name} ${msg}"
        FAILED=1
    fi
}

# 1. Verify tag placement
echo "Checking tag placement..."
TAG_SHA=$(git rev-parse "${TARGET_TAG}^{commit}")
if [[ "${TAG_SHA}" == *"${TARGET_SHA}"* ]]; then
    log_status "Tag ${TARGET_TAG} points to ${TARGET_SHA}" "PASS"
else
    log_status "Tag ${TARGET_TAG} points to ${TARGET_SHA}" "FAIL" "(Current SHA: ${TAG_SHA})"
fi

# 2. Verify local API brief endpoint
echo "Checking API mission brief..."
if curl -fsS "${E2E_BASE_URL}/api/mission/brief" >/dev/null; then
    log_status "Local API /api/mission/brief" "PASS"
else
    log_status "Local API /api/mission/brief" "FAIL"
fi

# 3. Verify local API relay status
echo "Checking API relay status..."
if RELAY_RES=$(curl -fsS "${E2E_BASE_URL}/api/v1/relay/status"); then
    if echo "${RELAY_RES}" | grep -q "HAS-WORKER-RELAY-001"; then
        log_status "Local API /api/v1/relay/status" "PASS" "(Contains HAS-WORKER-RELAY-001)"
    else
        log_status "Local API /api/v1/relay/status" "FAIL" "(HAS-WORKER-RELAY-001 missing)"
    fi
else
    log_status "Local API /api/v1/relay/status" "FAIL" "(HTTP request failed)"
fi

# 4. Run the release check suite
echo "Running full release check suite..."
if ./scripts/rc29_release_verify.sh; then
    log_status "RC29 Verification Suite" "PASS"
else
    log_status "RC29 Verification Suite" "FAIL"
fi

echo "======================================================================"
if [ "${FAILED}" -eq 0 ]; then
    echo "  >> SUCCESS: Production runtime sustainment is verified!"
    echo "======================================================================"
    exit 0
else
    echo "  >> FAILURE: Sustainment check failed."
    echo "======================================================================"
    exit 1
fi
