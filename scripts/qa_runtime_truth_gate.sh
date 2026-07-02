#!/usr/bin/env bash
# =============================================================================
# qa_runtime_truth_gate.sh
# Verifies that Swarm Ledger runtime truth signals are aligned.
# =============================================================================
set -euo pipefail

DB_PATH="backend/swarm_ledger.db"

echo "==> Running QA Runtime Truth Gate..."

if [ ! -f "$DB_PATH" ]; then
  echo "❌ FAIL: Swarm Ledger database '$DB_PATH' does not exist."
  exit 1
fi

CANON_UI=$(sqlite3 "${DB_PATH}" "SELECT value FROM runtime_truth_signals WHERE signal_id = 'canonical_ui_url';" 2>/dev/null || echo "")
if [ "${CANON_UI}" != "http://127.0.0.1:8765/ui-moonshot" ]; then
  echo "❌ FAIL: Runtime Truth 'canonical_ui_url' is wrong: '${CANON_UI}'"
  exit 1
fi

echo "✅ QA Runtime Truth Gate status: PASS"
exit 0
