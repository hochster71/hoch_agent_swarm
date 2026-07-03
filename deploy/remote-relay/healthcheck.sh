#!/usr/bin/env bash
# Simple remote relay healthcheck

echo "[info] Verifying local service health..."

# Check backend response
status_code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/prompt-brain/adapters/health)
if [ "$status_code" -ne 200 ]; then
  echo "[error] HAS Backend is unreachable (HTTP $status_code)."
  exit 1
fi

echo "[success] Local service health OK."
exit 0
