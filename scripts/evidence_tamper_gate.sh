#!/usr/bin/env bash
# =============================================================================
# evidence_tamper_gate.sh
# Bash wrapper executing the python evidence_tamper_gate.py script.
# =============================================================================
set -euo pipefail

python3 "$(dirname "$0")/evidence_tamper_gate.py" "$@"
