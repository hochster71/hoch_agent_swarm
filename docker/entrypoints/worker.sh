#!/usr/bin/env bash
set -euo pipefail

echo "==> Starting HAS Autonomy and Readiness Worker..."
exec /app/.venv/bin/python -c "
import time
from backend.readiness_daemon import ReadinessDaemon
daemon = ReadinessDaemon(interval_seconds=10)
daemon.start()
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    daemon.stop()
"
