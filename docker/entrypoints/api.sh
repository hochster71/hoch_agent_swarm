#!/usr/bin/env bash
set -euo pipefail

echo "==> Starting HAS API Gateway..."
# 0.0.0.0 is REQUIRED here: this runs INSIDE a container. Binding 127.0.0.1 would make
# the service unreachable through Docker's published-port mapping. The real exposure
# boundary is whether the host publishes the port (docker -p) + the host firewall — NOT
# the in-container bind. This is an accepted, container-scoped binding (not an SC-7 gap).
exec /app/.venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
