#!/usr/bin/env bash
# watchdog_loop.sh - Monitors uvicorn backend on port 8000 and reports events
set -euo pipefail

PROJECT_ROOT="/Users/michaelhoch/hoch_agent_swarm"
cd "$PROJECT_ROOT"

echo "[INFO] Watchdog loop started. Monitoring http://127.0.0.1:8000..."

while true; do
    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    # Check port 8000
    if ! nc -z 127.0.0.1 8000; then
        echo "[ERROR] [$TIMESTAMP] Backend service on port 8000 is unreachable!"
        
        # Log failure
        /Users/michaelhoch/.local/bin/uv run python -c "
import sqlite3, datetime, uuid
from backend.runtime_truth.state_store import DB_PATH
conn = sqlite3.connect(DB_PATH)
ts = datetime.datetime.now(datetime.UTC).isoformat()
conn.execute('INSERT INTO supervisor_events (event_id, timestamp, level, message) VALUES (?, ?, ?, ?)', (str(uuid.uuid4()), ts, 'ERROR', 'Backend port 8000 unreachable'))
conn.commit()
conn.close()
"
    else
        # Verify HTTP heartbeats endpoint
        HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/v1/runtime-truth/heartbeats || echo "000")
        if [ "$HTTP_STATUS" != "200" ]; then
            echo "[WARN] [$TIMESTAMP] Heartbeats API responded with status $HTTP_STATUS"
            /Users/michaelhoch/.local/bin/uv run python -c "
import sqlite3, datetime, uuid
from backend.runtime_truth.state_store import DB_PATH
conn = sqlite3.connect(DB_PATH)
ts = datetime.datetime.now(datetime.UTC).isoformat()
conn.execute('INSERT INTO supervisor_events (event_id, timestamp, level, message) VALUES (?, ?, ?, ?)', (str(uuid.uuid4()), ts, 'WARNING', 'Heartbeats endpoint responded with status ' + '$HTTP_STATUS'))
conn.commit()
conn.close()
"
        fi
    fi
    
    sleep 5
done
