#!/bin/zsh
# make_safe_handoff.sh — founder-friendly wrapper for fail-closed Kimi packs
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY="${ROOT}/scripts/kimi/make_safe_handoff.py"

if [[ $# -lt 1 ]]; then
  cat <<'USAGE'
Usage:
  scripts/kimi/make_safe_handoff.sh <path> [more paths...] [options]

Examples:
  # Dry-run scan only
  scripts/kimi/make_safe_handoff.sh scripts/qa/test-mesh-sentinel-contract.ts --dry-run

  # Pack a small public-ish UI snippet with a task
  scripts/kimi/make_safe_handoff.sh frontend/styles.css \
    --label ui-css-tweak \
    --task "Propose accessible contrast fixes for status pills only. No monorepo access."

  # Task from file
  scripts/kimi/make_safe_handoff.sh path/to/file.ts --task-file /tmp/task.md

  # Skip soft renames (still secret-redacts)
  scripts/kimi/make_safe_handoff.sh path --no-rename

Packs land in:
  ~/Documents/kimi/workspace/_inbox_from_helm/pack_*/

Kimi must deliver to:
  ~/Documents/kimi/workspace/_outbox_to_helm/pack_*/

Fail-closed: secrets / deny-list / residual keys refuse the pack.
USAGE
  exit 2
fi

exec python3 "$PY" "$@"
