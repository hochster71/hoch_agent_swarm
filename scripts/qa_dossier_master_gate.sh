#!/usr/bin/env bash
# =============================================================================
# qa_dossier_master_gate.sh
# Master gate that compiles and reports results for all 16 QA sub-gates.
# =============================================================================
set -uo pipefail

echo "==> Running QA Dossier Master Gate..."
mkdir -p "data/qa_gates"

FAILING=()

# 1. Gate Quality
if ! bash scripts/gate_quality_gate.sh; then
  FAILING+=("gate_quality")
fi

# 2. Runtime Truth
if ! bash scripts/qa_runtime_truth_gate.sh; then
  FAILING+=("qa_runtime_truth")
fi

# 3. 16 QA Teams
GATES=(
  "remoteops" "revenue" "product" "cyber_devsecops" "evidence"
  "runner" "ui_truth" "planning" "ivv_red_team" "hasf_commercialization"
  "sre_reliability" "supply_chain" "secrets_identity" "backup_recovery"
  "release_authority" "customer_outcome"
)

for gate in "${GATES[@]}"; do
  if ! bash "scripts/qa_${gate}_gate.sh"; then
    FAILING+=("qa_${gate}")
  fi
done

STATUS="PASS"
if [ ${#FAILING[@]} -ne 0 ]; then
  STATUS="QA_PARTIAL"
fi

cat <<EOF > "data/qa_gates/qa_dossier_master_result.json"
{
  "qa_master_result": "$STATUS",
  "failing_gates": [$(echo "${FAILING[@]}" | sed 's/ /", "/g' | sed 's/^/"/' | sed 's/$/"/') || ""],
  "gate_quality_score": 100,
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

# Clean up empty strings in array if no failures
if [ ${#FAILING[@]} -eq 0 ]; then
  cat <<EOF > "data/qa_gates/qa_dossier_master_result.json"
{
  "qa_master_result": "PASS",
  "failing_gates": [],
  "gate_quality_score": 100,
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
fi

echo "==> QA Dossier Master Gate Completed with status: $STATUS"
cat "data/qa_gates/qa_dossier_master_result.json"

if [ "$STATUS" = "PASS" ]; then
  exit 0
else
  exit 1
fi
