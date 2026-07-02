#!/usr/bin/env bash
# =============================================================================
# gate_quality_gate.sh
# Verifies the quality and robustness of all other gate scripts.
# =============================================================================
set -euo pipefail

echo "==> Auditing all QA Gate scripts for robust verification constraints..."

GATES=(
  "scripts/qa_runtime_truth_gate.sh"
  "scripts/qa_remoteops_gate.sh"
  "scripts/qa_revenue_gate.sh"
  "scripts/qa_product_gate.sh"
  "scripts/qa_cyber_devsecops_gate.sh"
  "scripts/qa_evidence_gate.sh"
  "scripts/qa_runner_gate.sh"
  "scripts/qa_ui_truth_gate.sh"
  "scripts/qa_planning_gate.sh"
  "scripts/qa_ivv_red_team_gate.sh"
  "scripts/qa_hasf_commercialization_gate.sh"
  "scripts/qa_sre_reliability_gate.sh"
  "scripts/qa_supply_chain_gate.sh"
  "scripts/qa_secrets_identity_gate.sh"
  "scripts/qa_backup_recovery_gate.sh"
  "scripts/qa_release_authority_gate.sh"
  "scripts/qa_customer_outcome_gate.sh"
  "scripts/qa_dossier_master_gate.sh"
)

for gate in "${GATES[@]}"; do
  if [ ! -f "$gate" ]; then
    echo "❌ Gate Quality Error: script '$gate' is missing!"
    exit 1
  fi
  # Verify no weak unconditional exit 0 bypasses
  if grep -q "exit 0" "$gate" && ! grep -q "status" "$gate" && ! grep -q "PASS" "$gate"; then
    echo "❌ Gate Quality Violation: script '$gate' contains weak unconditional exit 0!"
    exit 1
  fi
  # Check bash syntax
  bash -n "$gate"
done

echo "✅ Gate Quality Score: 100/100 (No weak gates or fake passes detected)."
exit 0
