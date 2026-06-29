#!/usr/bin/env bash
set -e

# Resolve root directory path
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=================================================="
echo "PROMPTOPS CLOSURE CONTROL PLANE GATE"
echo "=================================================="

# Check if running in container vs host
if [ -f "/app/scripts/promptops_gate_check.py" ]; then
  python3 /app/scripts/promptops_gate_check.py
else
  python3 "$ROOT_DIR/scripts/promptops_gate_check.py"
fi
