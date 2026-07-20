#!/usr/bin/env bash
# One-click evidence run for the Knowledge Engine (EDR-0004 v1).
# Read-only: exercises new non-frozen modules only; touches no live state.
# Founder click == authorization for this run (Python exec is approval-gated).
set -euo pipefail
cd "$(dirname "$0")/.."
echo "== EDR-0004 Knowledge Engine — v1 Governed Retrieval — test suite =="
python3 -m pytest tests/helm_runtime/test_knowledge_engine.py -v
