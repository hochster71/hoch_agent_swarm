#!/usr/bin/env bash
# ==============================================================================
# scripts/has_parallel_mirror_verify.sh
# ==============================================================================
# Parallel mirror verification script. Independently verifies:
#   - Git branch, HEAD tag v0.1.7 location
#   - SQLite DB tables
#   - Relay and port 3012 security
#   - API health
#   - Telemetry integrity (anti-fake verification)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Activate virtualenv
if [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

python3 "$PROJECT_ROOT/scripts/has_parallel_mirror_verify.py"
