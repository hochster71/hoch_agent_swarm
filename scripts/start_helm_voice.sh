#!/usr/bin/env bash
# Start (or restart) HELM LIVE with voice + ElevenLabs env loaded.
# Usage: bash scripts/start_helm_voice.sh
# Never prints secrets. Keys live in gitignored .env / .env.elevenlabs only.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PORT="${HELM_VOICE_PORT:-8770}"
PY="${ROOT}/.venv/bin/python"
LOG_OUT="${ROOT}/logs/helm_live_voice.out.log"
LOG_ERR="${ROOT}/logs/helm_live_voice.err.log"
mkdir -p "${ROOT}/logs"

# Load secrets without echoing them
set -a
if [[ -f "${ROOT}/.env" ]]; then
  # shellcheck disable=SC1091
  source "${ROOT}/.env"
fi
if [[ -f "${ROOT}/.env.elevenlabs" ]]; then
  # shellcheck disable=SC1091
  source "${ROOT}/.env.elevenlabs"
fi
set +a

# Free port if an old HELM LIVE is holding it
if command -v lsof >/dev/null 2>&1; then
  PIDS="$(lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN -t 2>/dev/null | sort -u || true)"
  if [[ -n "${PIDS}" ]]; then
    echo "Stopping existing listeners on :${PORT}"
    # shellcheck disable=SC2086
    kill ${PIDS} 2>/dev/null || true
    sleep 2
    PIDS2="$(lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN -t 2>/dev/null | sort -u || true)"
    if [[ -n "${PIDS2}" ]]; then
      # shellcheck disable=SC2086
      kill -9 ${PIDS2} 2>/dev/null || true
      sleep 1
    fi
  fi
fi

if [[ ! -x "${PY}" ]]; then
  echo "Missing ${PY} — run: uv sync  (or create .venv)"
  exit 1
fi

echo "Starting HELM LIVE voice on 0.0.0.0:${PORT}"
nohup "${PY}" -m uvicorn backend.helm_live_api:app --host 0.0.0.0 --port "${PORT}" \
  >"${LOG_OUT}" 2>"${LOG_ERR}" &
echo "pid $!"

# Wait for voice health
for i in $(seq 1 20); do
  code="$(curl -s -o /tmp/helm_voice_health.json -w '%{http_code}' --connect-timeout 1 \
    "http://127.0.0.1:${PORT}/api/v1/helm/voice/health" 2>/dev/null || echo fail)"
  if [[ "${code}" == "200" ]]; then
    echo "voice health: OK"
    curl -s "http://127.0.0.1:${PORT}/api/v1/helm/voice/tts/status" \
      | python3 -c "import sys,json; d=json.load(sys.stdin); e=d.get('providers',{}).get('elevenlabs',{}); print('elevenlabs:', e.get('status'), 'ready=', e.get('ready'))"
    echo "desk: http://127.0.0.1:${PORT}/voice"
    exit 0
  fi
  sleep 0.5
done
echo "voice health: FAILED (see ${LOG_ERR})"
tail -20 "${LOG_ERR}" 2>/dev/null || true
exit 1
