#!/usr/bin/env bash
# =============================================================================
# remote_goal_runner_cron.sh
# Periodically writes the heartbeat JSON for 24/7 monitoring.
# =============================================================================
set -euo pipefail

cat <<EOT > /root/hoch_agent_swarm/runner_heartbeat.json
{
  "component": "remote_goal_runner",
  "status": "RUNNING",
  "last_seen": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOT

echo "Heartbeat generated at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
