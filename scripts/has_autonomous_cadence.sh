#!/usr/bin/env bash
# ==============================================================================
# scripts/has_autonomous_cadence.sh
# ==============================================================================
# HAS/HASF Autonomous Cadence loop script.
# Safely pulls current repo, asserts tag v0.1.7, runs sustainment verification,
# runs parallel mirror verification, updates dashboard metrics, and blocks
# high-risk actions before printing the concise operator brief.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Activate virtualenv
if [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

python3 "$PROJECT_ROOT/scripts/has_autonomous_cadence.py"
