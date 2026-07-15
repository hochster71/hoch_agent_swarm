#!/usr/bin/env bash
# Foreground HELM LIVE for launchd KeepAlive (loads gitignored env, then exec).
# Do not use for interactive shells — use scripts/start_helm_voice.sh instead.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PORT="${HELM_VOICE_PORT:-8770}"
PY="${ROOT}/.venv/bin/python"
[[ -x "${PY}" ]] || PY="$(command -v python3)"

set -a
# shellcheck disable=SC1091
[[ -f "${ROOT}/.env" ]] && source "${ROOT}/.env"
# shellcheck disable=SC1091
[[ -f "${ROOT}/.env.elevenlabs" ]] && source "${ROOT}/.env.elevenlabs"
set +a

export PATH="${HOME}/.local/bin:/opt/homebrew/bin:/usr/local/bin:${PATH}"
exec "${PY}" -m uvicorn backend.helm_live_api:app --host 0.0.0.0 --port "${PORT}"
