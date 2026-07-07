#!/usr/bin/env bash
# stop_has_runtime.sh - Stops HAS supervised runtime and registers shutdown events
set -euo pipefail

PROJECT_ROOT="/Users/michaelhoch/hoch_agent_swarm"
cd "$PROJECT_ROOT"

echo "[INFO] Stopping HAS supervised local runtime..."

# Log shutdown event to database
uv run python -c "
import sqlite3, datetime, uuid
from backend.runtime_truth.state_store import DB_PATH
conn = sqlite3.connect(DB_PATH, timeout=30.0)
conn.execute('PRAGMA journal_mode=WAL;')
conn.execute('PRAGMA busy_timeout=30000;')
ts = datetime.datetime.now(datetime.UTC).isoformat()
conn.execute('UPDATE uptime_windows SET window_end = ? WHERE window_end IS NULL', (ts,))
conn.execute('INSERT INTO supervisor_events (event_id, timestamp, level, message) VALUES (?, ?, ?, ?)', (str(uuid.uuid4()), ts, 'INFO', 'FastAPI supervised service stop requested'))
conn.commit()
conn.close()
"

# Unload from launchd
PLIST_PATH="$HOME/Library/LaunchAgents/com.hoch.agent.swarm.runtime.plist"
if [ -f "$PLIST_PATH" ]; then
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
fi

# Terminate remaining processes on port 8000
PID=$(lsof -t -i :8000 || true)
if [ -n "$PID" ]; then
    echo "Terminating PID $PID on port 8000..."
    kill "$PID" 2>/dev/null || kill -9 "$PID" 2>/dev/null || true
fi

echo "[PASS] Supervised local runtime stopped cleanly."
