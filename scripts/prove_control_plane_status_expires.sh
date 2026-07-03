#!/usr/bin/env bash
set -euo pipefail

cd /Users/michaelhoch/hoch_agent_swarm

echo "=== TASK A7: PROVING CONTROL PLANE STATUS EXPIRES ==="

# 1. Build status with 2s expiry
echo "Building status file with 2s expiry..."
STATUS_MAX_AGE_SECONDS=2 python3 scripts/build_control_plane_status.py

# 2. Check if fresh initially (now < expires_at)
python3 - <<'PY'
import json
import datetime
import sys

with open("has_live_project_tracker/data/control_plane_status.json", "r") as f:
    data = json.load(f)

expires_at = datetime.datetime.fromisoformat(data["expires_at"].rstrip("Z").split("+")[0]).replace(tzinfo=datetime.timezone.utc)
now = datetime.datetime.now(datetime.timezone.utc)
if now > expires_at:
    print("❌ Error: Already expired on build!")
    sys.exit(1)
print("🟢 Initially FRESH.")
PY

# 3. Sleep 3 seconds
echo "Sleeping 3 seconds for expiry..."
sleep 3

# 4. Verify it is now expired
python3 - <<'PY'
import json
import datetime
import sys

with open("has_live_project_tracker/data/control_plane_status.json", "r") as f:
    data = json.load(f)

expires_at = datetime.datetime.fromisoformat(data["expires_at"].rstrip("Z").split("+")[0]).replace(tzinfo=datetime.timezone.utc)
now = datetime.datetime.now(datetime.timezone.utc)
if now <= expires_at:
    print("❌ Error: Should have expired, but is still considered fresh!")
    sys.exit(1)
print("🟢 Successfully detected EXPIRED/STALE state!")
PY

# 5. Restore standard status file (default 60s max_age)
echo "Restoring standard control plane status..."
python3 scripts/build_control_plane_status.py

echo "🟢 All expiry proof tests validated successfully!"
