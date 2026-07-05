#!/usr/bin/env bash
# ============================================================================
# HAS Burn-In "Warp Speed" Orchestrator — AI-accelerated CALENDAR-TIME
# efficiency, NOT wall-clock compression.
#
# WHAT THIS SCRIPT DOES:
#   1. AI-driven pre-flight (shift-left) — catches defects BEFORE the clock
#      starts, so the run you commit to has the highest possible chance of
#      completing clean on the first try. This is where real time is saved:
#      avoiding a restart at hour 14 is worth more than any clock trick.
#   2. Hard restart-guard — makes it structurally difficult to accidentally
#      reset the clock (the actual #1 time-waster observed this session:
#      4 unplanned restarts today).
#   3. Real-time AI-style anomaly watch — polls every 10s (not the usual
#      slow interval), scores deviation from healthy baseline, and pages
#      IMMEDIATELY on drift — reducing MTTD from "hours until someone checks"
#      to seconds, per 2026 SRE practice (MTTD 52min -> 7min case pattern).
#   4. Front-loaded + combinatorial fault injection — fires early in the
#      window, and can combine 2 faults at once, so recovery gaps surface
#      in minutes, not near the finish line.
#   5. Derive-only verdict at the end — reads the REAL ledger, REAL systemd
#      timestamps, REAL injection results. Cannot report GO early.
#
# WHAT THIS SCRIPT DOES NOT DO, EVER:
#   - It does NOT shorten the pre-registered 24h minimum wall-clock floor.
#   - It does NOT accept simulated cycles as real cycles.
#   - It does NOT let you "finish early" — GO is only ever derived from
#     (now - ActiveEnterTimestamp) >= ORACLE.min_wall_clock_hours, measured
#     against the actual systemd unit on the actual host, every time.
#
# If you want the 24h FLOOR ITSELF changed (not just used more efficiently),
# that is a Configuration Change Request through your CCB with a Security
# Impact Analysis citing historical burn-in data — see the cm-path command.
# ============================================================================

set -euo pipefail

# ---- CONFIG ----------------------------------------------------------------
REMOTE_HOST="root@100.87.18.15"
UNIT="hoch-ag-execution-daemon.service"
REPO="/root/hoch_agent_swarm"
ORACLE_PATH="$REPO/has_live_project_tracker/data/ag_execution_burn_in_oracle.json"
GUARD_LOCK="$REPO/has_live_project_tracker/data/.burn_in_guard.lock"
POLL_SECONDS=10          # AI-style tight poll, not the usual 60-300s
LOCAL_LOG="/tmp/has_burn_in_watch_$(date +%Y%m%d_%H%M%S).log"

log() { echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$LOCAL_LOG"; }

# ============================================================================
# S1. AI PRE-FLIGHT (shift-left) - run BEFORE touching the daemon.
#     Goal: maximize probability this run completes clean, so you never pay
#     the cost of a restart. This is the single biggest real time-saver.
# ============================================================================
preflight() {
  log "=== S1 PRE-FLIGHT: shift-left defect scan (before clock starts) ==="

  log "-- static/lint pass on daemon + injector + lease code --"
  python3 -m py_compile \
    scripts/ag_execution_daemon.py \
    scripts/ag_execution_failure_injector.py \
    scripts/ag_execution_lease_manager.py 2>&1 | tee -a "$LOCAL_LOG" || {
      log "FAIL: syntax/compile error found. DO NOT START THE CLOCK. Fix first."
      exit 1
    }
