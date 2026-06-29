#!/usr/bin/env bash
set -euo pipefail

echo "==> Starting HAS API Gateway..."
exec /app/.venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
