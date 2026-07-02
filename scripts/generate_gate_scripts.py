import os

GATES = [
    "remoteops", "revenue", "product", "cyber_devsecops", "evidence",
    "runner", "ui_truth", "planning", "ivv_red_team", "hasf_commercialization",
    "sre_reliability", "supply_chain", "secrets_identity", "backup_recovery",
    "release_authority", "customer_outcome"
]

for gate in GATES:
    filename = f"scripts/qa_{gate}_gate.sh"
    content = f"""#!/usr/bin/env bash
# =============================================================================
# qa_{gate}_gate.sh
# Verification gate for the {gate} team dossier.
# =============================================================================
set -euo pipefail

DOSSIER_FILE="data/qa_dossiers/{gate}_qa.json"

echo "==> Probing {gate} QA dossier..."

if [ ! -f "$DOSSIER_FILE" ]; then
  echo "❌ FAIL: Dossier file '$DOSSIER_FILE' is missing!"
  exit 1
fi

STATUS=$(jq -r '.verification_status' "$DOSSIER_FILE" 2>/dev/null || echo "UNKNOWN")

if [ "$STATUS" != "PASS" ]; then
  echo "❌ FAIL: {gate} QA Status is '$STATUS'"
  echo "Unresolved defects:"
  jq -r '.unresolved_defects[]' "$DOSSIER_FILE" 2>/dev/null || echo "None"
  exit 1
fi

echo "✅ {gate} QA Dossier Verification Gate Passed."
exit 0
"""
    with open(filename, "w") as f:
        f.write(content)
    os.chmod(filename, 0o755)

print("Generated 16 gate shell scripts.")
