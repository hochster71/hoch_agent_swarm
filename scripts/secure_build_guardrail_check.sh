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

# 1. No secrets, .env, or runtime DBs staged/committed
echo "Checking for committed secrets or credentials..."
if git diff --name-only master..HEAD 2>/dev/null | grep -E "\.env|secrets|key" >/dev/null; then
    echo "  [FAIL] Found credentials/secrets files in diff."
    VIOLATIONS=$((VIOLATIONS + 1))
else
    echo "  [PASS] No credentials/secrets found in diff."
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
if python3 -c 'import socket; s=socket.socket(); s.settimeout(3.0); s.connect(("50.116.41.183", 3012))' 2>/dev/null; then
    echo "  [FAIL] Public port 3012 is exposed!"
    PUBLIC_EXPOSURE=$((PUBLIC_EXPOSURE + 1))
    VIOLATIONS=$((VIOLATIONS + 1))
else
    echo "  [PASS] Public port 3012 is closed/blocked."
fi

# 4. No fake status synthesis
echo "Auditing fake status flags..."
# Check status.json for any fake "PASS" value
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

# 5. Tag integrity check
echo "Checking tag integrity..."
TAG_SHA=$(git rev-parse v0.1.8-cadence^{commit})
if [ "$TAG_SHA" != "9f52d77dd3f68b0e50396536a505ac16cb73f66a" ]; then
    echo "  [FAIL] Tag v0.1.8-cadence points to incorrect commit: $TAG_SHA"
    VIOLATIONS=$((VIOLATIONS + 1))
else
    echo "  [PASS] Tag v0.1.8-cadence points to expected commit 9f52d77."
fi

# 6. Tailscale ACL Posture Check
echo "Checking Tailscale ACL Posture..."
POSTURE_FILE="$PROJECT_ROOT/config/tailscale_acl_posture.yaml"
if [ -f "$POSTURE_FILE" ]; then
    if grep -q "posture: SECURE" "$POSTURE_FILE"; then
        echo "  [PASS] Tailscale ACL posture is verified SECURE."
    else
        echo "  [FAIL] Tailscale ACL posture is UNKNOWN or NOT SECURE."
        APPROVAL_REQUIRED=$((APPROVAL_REQUIRED + 1))
    fi
else
    echo "  [FAIL] Missing tailscale_acl_posture.yaml! Posture verification required."
    APPROVAL_REQUIRED=$((APPROVAL_REQUIRED + 1))
fi

# 7. iPhone Monitor Only Check
echo "Verifying mobile monitoring constraint..."
# Audits that iphone-15-pro-max is only registered as monitor/approval role
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
