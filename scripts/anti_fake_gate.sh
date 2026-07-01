#!/usr/bin/env bash
# anti_fake_gate.sh - Core check for fake readiness and contradictions in HAS

set -euo pipefail

echo "==> Running Anti-Fake Gate Auditing..."

# Run python script to evaluate claims and verify contradictions
uv run python -c "
import sys
import sqlite3
from backend.runtime_truth.state_store import DB_PATH, apply_pragmas

conn = sqlite3.connect(DB_PATH)
apply_pragmas(conn)
conn.row_factory = sqlite3.Row

# Check active contradictions
contradictions = conn.execute('SELECT * FROM runtime_contradictions').fetchall()
if contradictions:
    print('FAIL: Contradictions detected in environment claims:')
    for c in contradictions:
        print(f' - ID: {c[\"id\"]}, claims: {c[\"claims\"]}')
    sys.exit(1)

# Check heartbeats
hb = conn.execute('SELECT * FROM runtime_heartbeats WHERE component = \"backend_core\"').fetchone()
if not hb:
    print('FAIL: Backend core heartbeat is missing.')
    sys.exit(1)

from datetime import datetime, timezone
now = datetime.now(timezone.utc)
hb_time = datetime.fromisoformat(hb['last_seen'])
if (now - hb_time).total_seconds() > 120.0:
    print(f'FAIL: Heartbeat is stale (age: {(now - hb_time).total_seconds()}s).')
    sys.exit(1)

print('SUCCESS: All anti-fake constraints checked and passing.')
"

exit 0
