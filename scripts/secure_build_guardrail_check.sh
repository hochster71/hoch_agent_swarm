#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
METRICS_FILE="$PROJECT_ROOT/has_live_project_tracker/data/guardrail_metrics.json"

echo "=================================================="
echo "SECURE BUILD GUARDRAILS CHECK"
echo "=================================================="

VIOLATIONS=0
PUBLIC_EXPOSURE=0
FAKE_STATUS=0
APPROVAL_REQUIRED=0

# 1. Run Python Guardrail Engine (Secrets, Compute Cost, Tag Policy, Tailscale Posture)
echo "Running Python Guardrail Engine..."
set +e
python3 "$SCRIPT_DIR/secure_build_guardrail_check.py"
PY_EXIT=$?
set -e

if [ $PY_EXIT -ne 0 ]; then
    echo "  [FAIL] Python Guardrail Engine detected violations."
    VIOLATIONS=$((VIOLATIONS + 1))
else
    echo "  [PASS] Python Guardrail Engine checks passed."
fi

# Fetch Tailscale Posture from python helper output/check
set +e
POSTURE=$(python3 -c "import sys; sys.path.append('$SCRIPT_DIR'); import secure_build_guardrail_check; print(secure_build_guardrail_check.verify_tailscale_posture())" 2>/dev/null)
set -e
if [ "$POSTURE" = "VERIFIED" ]; then
    echo "  [PASS] Tailscale ACL posture is verified SECURE/LIVE."
else
    echo "  [FAIL] Tailscale ACL posture status: $POSTURE"
    APPROVAL_REQUIRED=$((APPROVAL_REQUIRED + 1))
fi

# 2. No runtime DBs committed
if git diff --name-only master..HEAD 2>/dev/null | grep -E "\.db$" >/dev/null; then
    echo "  [FAIL] Found SQLite database file in diff."
    VIOLATIONS=$((VIOLATIONS + 1))
else
    echo "  [PASS] No SQLite database files committed."
fi

# 3. No public 3012 exposure
echo "Testing public port 3012 unreachable..."
HOCH_200_IP=$(python3 -c "import json, pathlib; r=pathlib.Path('$PROJECT_ROOT/config/compute_assets.json'); cfg=json.loads(r.read_text()); print([a for a in cfg['assets'] if a['id']=='hoch-200'][0]['public_ip'])" 2>/dev/null || echo "50.116.41.183")
if python3 -c "import socket; s=socket.socket(); s.settimeout(3.0); s.connect((\"$HOCH_200_IP\", 3012))" 2>/dev/null; then
    echo "  [FAIL] Public port 3012 is exposed on $HOCH_200_IP!"
    PUBLIC_EXPOSURE=$((PUBLIC_EXPOSURE + 1))
    VIOLATIONS=$((VIOLATIONS + 1))
else
    echo "  [PASS] Public port 3012 on $HOCH_200_IP is closed/blocked."
fi

# 4. No fake status synthesis
echo "Auditing fake status flags..."
STATUS_JSON="$PROJECT_ROOT/has_live_project_tracker/data/status.json"
if [ -f "$STATUS_JSON" ]; then
    if grep -q '"status": "PASS"' "$STATUS_JSON"; then
        echo "  [FAIL] Found fake status 'PASS' in status.json."
        FAKE_STATUS=$((FAKE_STATUS + 1))
        VIOLATIONS=$((VIOLATIONS + 1))
    else
        echo "  [PASS] No fake status flags found in status.json."
    fi
else
    echo "  [PASS] status.json not found."
fi

# 5. iPhone Monitor Only Check
echo "Verifying mobile monitoring constraint..."
if grep -q "machine: \"iphone-15-pro-max\"" "$PROJECT_ROOT/config/usage_budget_policy.yaml"; then
    echo "  [PASS] iPhone configured as operator mobile monitor only."
else
    echo "  [FAIL] iPhone is not configured with operator mobile monitor policy."
    VIOLATIONS=$((VIOLATIONS + 1))
fi

# Write JSON metrics
mkdir -p "$(dirname "$METRICS_FILE")"
cat <<EOF > "$METRICS_FILE"
{
  "security_guardrail_violations": $VIOLATIONS,
  "public_exposure_violations": $PUBLIC_EXPOSURE,
  "fake_status_violations": $FAKE_STATUS,
  "approval_required_count": $APPROVAL_REQUIRED,
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF

echo "=================================================="
if [ "$VIOLATIONS" -eq 0 ]; then
    echo ">> SUCCESS: Secure Build Guardrails PASS!"
    echo "=================================================="
    exit 0
else
    echo ">> FAILURE: $VIOLATIONS violations detected!"
    echo "=================================================="
    exit 1
fi
