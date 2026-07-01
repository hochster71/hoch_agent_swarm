#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
METRICS_FILE="$PROJECT_ROOT/has_live_project_tracker/data/usage_metrics.json"

# Default limits
MAX_FILES=10
MAX_SCRIPTS=3
MAX_TESTS=2

# Count changes against master
cd "$PROJECT_ROOT"
FILES_CHANGED=$(git diff --name-only master..HEAD 2>/dev/null | wc -l | tr -d ' ')
NEW_SCRIPTS=$(git diff --name-only master..HEAD 2>/dev/null | grep "^scripts/" | wc -l | tr -d ' ')
NEW_TESTS=$(git diff --name-only master..HEAD 2>/dev/null | grep -E "tests/|\.spec\." | wc -l | tr -d ' ')

# Calculate runtime duration (mock/approx duration since branch start, e.g. 5 minutes for proof)
ELAPSED=5

RISK="LOW"
if [ "$FILES_CHANGED" -gt "$MAX_FILES" ] || [ "$NEW_SCRIPTS" -gt "$MAX_SCRIPTS" ] || [ "$NEW_TESTS" -gt "$MAX_TESTS" ]; then
    RISK="HIGH"
elif [ "$FILES_CHANGED" -gt 8 ]; then
    RISK="MEDIUM"
fi

# Construct JSON manually to avoid dependencies
mkdir -p "$(dirname "$METRICS_FILE")"
cat <<EOF > "$METRICS_FILE"
{
  "ag_usage_risk": "$RISK",
  "files_changed_this_cycle": $FILES_CHANGED,
  "elapsed_minutes_this_cycle": $ELAPSED,
  "new_scripts_count": $NEW_SCRIPTS,
  "new_tests_count": $NEW_TESTS,
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF

echo "=================================================="
echo "AG USAGE BUDGET CHECK"
echo "=================================================="
echo "Usage Risk Score:    $RISK"
echo "Files Changed:       $FILES_CHANGED (Max: $MAX_FILES)"
echo "New Scripts:         $NEW_SCRIPTS (Max: $MAX_SCRIPTS)"
echo "New Tests:           $NEW_TESTS (Max: $MAX_TESTS)"
echo "=================================================="
