#!/usr/bin/env bash
set -euo pipefail

cd /Users/michaelhoch/hoch_agent_swarm
mkdir -p logs

while true; do
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Michaels AI Model GOAL runner cycle start" >> logs/has_goal_runner_daemon.log
  RUN_LEGACY_RELEASE_GATES=0 RUN_FULL_LEGACY_PLAYWRIGHT=0 bash scripts/has_goal_e2e_runner.sh >> logs/has_goal_runner_daemon.log 2>&1 || true
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Michaels AI Model GOAL runner cycle complete" >> logs/has_goal_runner_daemon.log
  sleep 600
done
