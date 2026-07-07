#!/usr/bin/env bash
# Verify the Apple Calendar adapter OFFLINE.
#   1. py_compile every service module (must compile without caldav installed).
#   2. Run the security + redaction test suites.
# Exit 0 only if ALL steps pass.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

PYTHON="python3"
if [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
  PYTHON="${REPO_ROOT}/.venv/bin/python"
fi

SVC_DIR="services/apple_calendar_adapter"

echo "== [1/2] py_compile service modules =="
"${PYTHON}" -m py_compile \
  "${SVC_DIR}/__init__.py" \
  "${SVC_DIR}/app.py" \
  "${SVC_DIR}/models.py" \
  "${SVC_DIR}/redaction.py" \
  "${SVC_DIR}/ledger.py"
echo "   OK — all modules compiled."

echo "== [2/2] security + redaction test suites =="
"${PYTHON}" -m pytest -q \
  tests/test_apple_calendar_adapter_security.py \
  tests/test_apple_calendar_adapter_redaction.py

echo "== VERIFY PASSED =="
