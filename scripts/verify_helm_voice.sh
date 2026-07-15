#!/usr/bin/env bash
# Smoke HELM voice + TTS + optional Tailscale origin.
set -euo pipefail
LOCAL="${HELM_LOCAL:-http://127.0.0.1:8770}"
TAIL="${HELM_TAILNET:-https://michaels-macbook-pro.tail826763.ts.net}"

check() {
  local name="$1" url="$2"
  local code
  code="$(curl -sk -o /tmp/hv_check.json -w '%{http_code}' --connect-timeout 5 "$url" || echo fail)"
  if [[ "$code" == "200" ]]; then
    echo "OK  $name"
  else
    echo "FAIL $name ($code)"
    return 1
  fi
}

echo "=== HELM Voice verify ==="
check "local health" "$LOCAL/api/v1/helm/voice/health"
check "local tts" "$LOCAL/api/v1/helm/voice/tts/status"
check "local brief" "$LOCAL/api/v1/helm/voice/brief"
check "local voice page" "$LOCAL/voice"
check "tailnet health" "$TAIL/api/v1/helm/voice/health" || true
check "tailnet voice page" "$TAIL/voice" || true

python3 - <<'PY'
import json
from pathlib import Path
p=Path("/tmp/hv_check.json")
# last check may be voice page html — load tts separately not required
print("verify script complete")
PY

echo "phone: $TAIL/voice"
echo "local: $LOCAL/voice"
