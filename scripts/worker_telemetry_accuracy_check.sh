#!/usr/bin/env bash
# scripts/worker_telemetry_accuracy_check.sh
# Shell wrapper to run the worker telemetry accuracy check python script.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Activate virtualenv if present
if [ -d "$PROJECT_ROOT/.venv" ]; then
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

python3 "$SCRIPT_DIR/worker_telemetry_accuracy_check.py"
