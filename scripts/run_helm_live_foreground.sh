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
# Zero-Trust: bind loopback only (SC-7). This launcher is RETIRED (its launchd job
# com.hoch.helm.voice is disabled); the hardened autoloop is the live supervisor.
exec "${PY}" -m uvicorn backend.helm_live_api:app --host 127.0.0.1 --port "${PORT}"
