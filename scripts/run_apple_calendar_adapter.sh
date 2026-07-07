#!/usr/bin/env bash
# Start the Apple Calendar CalDAV adapter on 127.0.0.1:8011 (loopback ONLY).
#
# Security: binds loopback only; never 0.0.0.0. Read-only by default.
# The app-specific password is resolved at runtime from the macOS Keychain
# (preferred) or the environment — it is NOT read or printed by this script.
set -euo pipefail

# Repo root = two levels up from this script (scripts/ -> repo).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

HOST="127.0.0.1"
PORT="8011"

# Default to read-only unless the operator has explicitly opted in.
export APPLE_CALENDAR_MODE="${APPLE_CALENDAR_MODE:-read_only}"

echo "[apple-calendar-adapter] mode=${APPLE_CALENDAR_MODE} binding ${HOST}:${PORT} (loopback only)"

# Prefer a dedicated venv if present; otherwise rely on the active interpreter.
PYTHON="python3"
if [[ -x "${REPO_ROOT}/.venv-apple/bin/python" ]]; then
  PYTHON="${REPO_ROOT}/.venv-apple/bin/python"
fi

exec "${PYTHON}" -m uvicorn \
  services.apple_calendar_adapter.app:app \
  --host "${HOST}" \
  --port "${PORT}" \
  --no-access-log
