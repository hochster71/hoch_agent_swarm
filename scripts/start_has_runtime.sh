#!/usr/bin/env bash
# start_has_runtime.sh - Starts uvicorn FastAPI backend under launchd supervision
set -euo pipefail

PROJECT_ROOT="/Users/michaelhoch/hoch_agent_swarm"
cd "$PROJECT_ROOT"

mkdir -p data/backups

echo "[$(date)] Starting FastAPI backend server on 127.0.0.1:8000..." >> data/backups/supervisor.log

# Log boot event to database
/Users/michaelhoch/.local/bin/uv run python -c "
import sqlite3, datetime, uuid
from backend.runtime_truth.state_store import DB_PATH
conn = sqlite3.connect(DB_PATH, timeout=30.0)
conn.execute('PRAGMA journal_mode=WAL;')
conn.execute('PRAGMA busy_timeout=30000;')
ts = datetime.datetime.now(datetime.UTC).isoformat()
conn.execute('INSERT OR REPLACE INTO uptime_windows (window_start, window_end, status) VALUES (?, NULL, ?)', (ts, 'ACTIVE'))
conn.execute('INSERT INTO supervisor_events (event_id, timestamp, level, message) VALUES (?, ?, ?, ?)', (str(uuid.uuid4()), ts, 'INFO', 'FastAPI supervised service start'))
conn.commit()
conn.close()
"

# Launch in foreground using exec to let launchd monitor the process
export PATH="/Users/michaelhoch/.local/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
TEST_MODE=true exec /Users/michaelhoch/.local/bin/uv run python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
