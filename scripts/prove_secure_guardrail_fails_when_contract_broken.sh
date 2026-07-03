#!/usr/bin/env bash
set -eo pipefail

echo "=== TASK 8: PROVING SECURE GUARDRAIL FAILS WHEN CONTRACT IS BROKEN ==="

# Define files
COMPUTE_JSON="config/compute_assets.json"
COMPUTE_BAK="config/compute_assets.json.bak"
TAG_JSON="config/release_tag_policy.json"
TAG_BAK="config/release_tag_policy.json.bak"
PLANTED_ENV=".env.planted_failure"

# Cleanup on exit
cleanup() {
  if [ -f "$COMPUTE_BAK" ]; then
    echo "Restoring $COMPUTE_JSON..."
    mv "$COMPUTE_BAK" "$COMPUTE_JSON"
  fi
  if [ -f "$TAG_BAK" ]; then
    echo "Restoring $TAG_JSON..."
    mv "$TAG_BAK" "$TAG_JSON"
  fi
  if [ -f "$PLANTED_ENV" ]; then
    echo "Deleting $PLANTED_ENV..."
    rm -f "$PLANTED_ENV"
  fi
}
trap cleanup EXIT

# -------------------------------------------------------------
# A. Secret-content planted failure
# -------------------------------------------------------------
echo "Test A: Creating planted secret file $PLANTED_ENV..."
echo "OPENAI_API_KEY=sk-planted-failure-not-real" > "$PLANTED_ENV"

set +e
echo "Running guardrail..."
bash scripts/secure_build_guardrail_check.sh > test_a_output.log 2>&1
EXIT_A=$?
set -e

cat test_a_output.log
rm -f "$PLANTED_ENV"

if [ $EXIT_A -eq 0 ]; then
  echo "❌ Failure: Guardrail passed despite planted secret file!"
  exit 1
else
  echo "🟢 Pass: Guardrail failed as expected on planted secret."
fi

# -------------------------------------------------------------
# B. Cost double-count planted failure
# -------------------------------------------------------------
echo "Test B: Backing up and modifying compute assets cost..."
cp "$COMPUTE_JSON" "$COMPUTE_BAK"
# Temporarily set linode-remote-60 billable to true and cost to 60
python3 -c "
import json
with open('$COMPUTE_JSON', 'r') as f:
    cfg = json.load(f)
for a in cfg['assets']:
    if a['id'] == 'linode-remote-60':
        a['billable'] = True
        a['monthly_cost_usd'] = 60
with open('$COMPUTE_JSON', 'w') as f:
    json.dump(cfg, f, indent=2)
"

set +e
echo "Running guardrail..."
bash scripts/secure_build_guardrail_check.sh > test_b_output.log 2>&1
EXIT_B=$?
set -e

cat test_b_output.log
mv "$COMPUTE_BAK" "$COMPUTE_JSON"

if [ $EXIT_B -eq 0 ]; then
  echo "❌ Failure: Guardrail passed despite double billing configuration!"
  exit 1
else
  echo "🟢 Pass: Guardrail failed as expected on double billing."
fi

# -------------------------------------------------------------
# C. Tag policy planted failure
# -------------------------------------------------------------
echo "Test C: Backing up and modifying tag policy..."
cp "$TAG_JSON" "$TAG_BAK"
# Set expected_commit to impossible SHA
python3 -c "
import json
with open('$TAG_JSON', 'r') as f:
    cfg = json.load(f)
cfg['expected_commit'] = '0000000000000000000000000000000000000000'
with open('$TAG_JSON', 'w') as f:
    json.dump(cfg, f, indent=2)
"

set +e
echo "Running guardrail..."
bash scripts/secure_build_guardrail_check.sh > test_c_output.log 2>&1
EXIT_C=$?
set -e

cat test_c_output.log
mv "$TAG_BAK" "$TAG_JSON"

if [ $EXIT_C -eq 0 ]; then
  echo "❌ Failure: Guardrail passed despite incorrect tag commit!"
  exit 1
else
  echo "🟢 Pass: Guardrail failed as expected on tag mismatch."
fi

echo "🟢 All Task 8 planted failures tested and validated successfully!"
exit 0
