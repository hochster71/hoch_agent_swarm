# Start/Stop SQLite Hardening Verification

## HEAD
0a7d3d570128f4f35c09ca94c300d419e509b82f
0a7d3d5 Harden provider key provisioning script
e1216e2 feat(r1): guided provider API-key provisioning script (opens key page, hidden paste, .env store)
0c50cdc Harden HOCH-200 mission commander truth dashboard
432eb73 fix(pert): wire tests/evidence/accountability/blocked to real sources (UNKNOWN if missing); guard: no hardcoded metric literals
305cc5a fix(pert): derived goal-percent wins over stale cadence-cache override (no more 80)
1a39384 fix(pert): unify goal-percent to ONE weighted source (buildout 50% + revenue 50%); kills the 80% override

## Scoped status
 M scripts/start_has_runtime.sh
 M scripts/stop_has_runtime.sh

## Scoped diff
diff --git a/scripts/start_has_runtime.sh b/scripts/start_has_runtime.sh
index a19e990..8a11826 100755
--- a/scripts/start_has_runtime.sh
+++ b/scripts/start_has_runtime.sh
@@ -13,7 +13,9 @@ echo "[$(date)] Starting FastAPI backend server on 127.0.0.1:8000..." >> data/ba
 /Users/michaelhoch/.local/bin/uv run python -c "
 import sqlite3, datetime, uuid
 from backend.runtime_truth.state_store import DB_PATH
-conn = sqlite3.connect(DB_PATH)
+conn = sqlite3.connect(DB_PATH, timeout=30.0)
+conn.execute('PRAGMA journal_mode=WAL;')
+conn.execute('PRAGMA busy_timeout=30000;')
 ts = datetime.datetime.now(datetime.UTC).isoformat()
 conn.execute('INSERT OR REPLACE INTO uptime_windows (window_start, window_end, status) VALUES (?, NULL, ?)', (ts, 'ACTIVE'))
 conn.execute('INSERT INTO supervisor_events (event_id, timestamp, level, message) VALUES (?, ?, ?, ?)', (str(uuid.uuid4()), ts, 'INFO', 'FastAPI supervised service start'))
diff --git a/scripts/stop_has_runtime.sh b/scripts/stop_has_runtime.sh
index 85ddef5..13e0564 100755
--- a/scripts/stop_has_runtime.sh
+++ b/scripts/stop_has_runtime.sh
@@ -11,7 +11,9 @@ echo "[INFO] Stopping HAS supervised local runtime..."
 uv run python -c "
 import sqlite3, datetime, uuid
 from backend.runtime_truth.state_store import DB_PATH
-conn = sqlite3.connect(DB_PATH)
+conn = sqlite3.connect(DB_PATH, timeout=30.0)
+conn.execute('PRAGMA journal_mode=WAL;')
+conn.execute('PRAGMA busy_timeout=30000;')
 ts = datetime.datetime.now(datetime.UTC).isoformat()
 conn.execute('UPDATE uptime_windows SET window_end = ? WHERE window_end IS NULL', (ts,))
 conn.execute('INSERT INTO supervisor_events (event_id, timestamp, level, message) VALUES (?, ?, ?, ?)', (str(uuid.uuid4()), ts, 'INFO', 'FastAPI supervised service stop requested'))

## Bash syntax

## Required SQLite hardening scan
scripts/start_has_runtime.sh:16:conn = sqlite3.connect(DB_PATH, timeout=30.0)
scripts/start_has_runtime.sh:17:conn.execute('PRAGMA journal_mode=WAL;')
scripts/start_has_runtime.sh:18:conn.execute('PRAGMA busy_timeout=30000;')
scripts/stop_has_runtime.sh:14:conn = sqlite3.connect(DB_PATH, timeout=30.0)
scripts/stop_has_runtime.sh:15:conn.execute('PRAGMA journal_mode=WAL;')
scripts/stop_has_runtime.sh:16:conn.execute('PRAGMA busy_timeout=30000;')

## Forbidden behavior scan
NO_FORBIDDEN_START_STOP_DIFFS

## Protected files

## Runtime containment
Containment CLEAN
