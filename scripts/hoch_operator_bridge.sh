#!/usr/bin/env bash
set -u

REPO="/Users/michaelhoch/hoch_agent_swarm"
EVIDENCE_DIR="$REPO/docs/evidence/ui"
SCREENSHOT_DIR="$EVIDENCE_DIR/screenshots"
REPORT="$EVIDENCE_DIR/20260630-chrome-crash-debug.md"

mkdir -p "$EVIDENCE_DIR" "$SCREENSHOT_DIR"

log() {
  printf "%s\n" "$*"
}

append_report() {
  printf "%s\n" "$*" >> "$REPORT"
}

safe_source_tracker_env() {
  if [ -f "$HOME/.hoch-secrets/has-tracker.env" ]; then
    # shellcheck disable=SC1090
    source "$HOME/.hoch-secrets/has-tracker.env"
    return 0
  fi
  return 1
}

init_report() {
  cat > "$REPORT" <<EOF
# Chrome P0 Crash Debug Evidence

- Time: $(date)
- Host: $(hostname)
- Repo: $REPO

## Verdict

PENDING

EOF
}

repo_check() {
  log "=== REPO CHECK ==="
  cd "$REPO" || exit 2
  pwd
  git rev-parse --show-toplevel
  git branch --show-current
  git status --short
}

tracker_check() {
  log "=== TRACKER CHECK ==="
  cd "$REPO" || exit 2

  if ! safe_source_tracker_env; then
    log "NO-GO: tracker env missing at ~/.hoch-secrets/has-tracker.env"
    return 1
  fi

  log "Checking authenticated /api/health without printing secrets..."
  curl -sS -i -u "${TRACKER_USER}:${TRACKER_PASSWORD}" \
    http://127.0.0.1:3001/api/health | sed -n '1,20p'

  log
  log "Checking authenticated /api/auth-check without printing secrets..."
  curl -sS -i -u "${TRACKER_USER}:${TRACKER_PASSWORD}" \
    http://127.0.0.1:3001/api/auth-check | sed -n '1,80p'
}

copy_tracker_password() {
  if ! safe_source_tracker_env; then
    log "NO-GO: tracker env missing at ~/.hoch-secrets/has-tracker.env"
    exit 1
  fi

  printf "%s" "$TRACKER_PASSWORD" | pbcopy
  log "Tracker password copied to clipboard."
}

kill_chrome() {
  log "=== KILLING CHROME ==="
  pkill -f "Google Chrome" 2>/dev/null || true
  pkill -f "Chrome Helper" 2>/dev/null || true
  sleep 2
  ps aux | grep -i "chrome" | grep -v grep || true
}

chrome_version() {
  log "=== CHROME VERSION ==="
  if [ -x "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ]; then
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --version || true
  else
    log "Google Chrome binary not found at /Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
  fi
}

chrome_clean_profile() {
  log "=== CHROME CLEAN PROFILE TEST ==="
  kill_chrome
  open -na "Google Chrome" --args \
    --user-data-dir=/tmp/chrome-has-clean-profile \
    --disable-extensions \
    --no-first-run \
    --disable-sync \
    http://127.0.0.1:3001

  log
  log "Observe Chrome for 20 seconds."
  read -r -p "Did Chrome stay open? Type y/n: " ans

  append_report "## Clean Profile Test"
  append_report ""
  append_report "- Result: $ans"
  append_report ""

  if [ "$ans" = "y" ] || [ "$ans" = "Y" ]; then
    log "RESULT: Clean profile stayed open."
    log "Likely root cause: normal Chrome profile/extensions/sync/cache corruption."
    append_report "Classification: profile/extensions/sync/cache likely corrupted."
    append_report ""
    append_report "Verdict: CONDITIONAL_GO — Chrome works with clean temporary profile."
    return 0
  fi

  log "RESULT: Clean profile still closed."
  append_report "Classification: clean profile failed; continue to GPU-disabled test."
  return 1
}

chrome_gpu_off() {
  log "=== CHROME GPU-DISABLED TEST ==="
  kill_chrome
  open -na "Google Chrome" --args \
    --user-data-dir=/tmp/chrome-has-gpu-off \
    --disable-gpu \
    --disable-extensions \
    --no-first-run \
    --disable-sync \
    http://127.0.0.1:3001

  log
  log "Observe Chrome for 20 seconds."
  read -r -p "Did GPU-disabled Chrome stay open? Type y/n: " ans

  append_report "## GPU Disabled Test"
  append_report ""
  append_report "- Result: $ans"
  append_report ""

  if [ "$ans" = "y" ] || [ "$ans" = "Y" ]; then
    log "RESULT: GPU-disabled Chrome stayed open."
    log "Likely root cause: GPU/hardware acceleration/WebGL crash."
    append_report "Classification: GPU/hardware acceleration/WebGL issue likely."
    append_report ""
    append_report "Verdict: CONDITIONAL_GO — Chrome works with GPU disabled."
    return 0
  fi

  log "RESULT: GPU-disabled Chrome still closed."
  append_report "Classification: clean profile and GPU-disabled both failed."
  return 1
}

chrome_crash_reports() {
  log "=== CHROME CRASH REPORTS ==="

  append_report "## Crash Reports"
  append_report ""

  ls -lt "$HOME"/Library/Logs/DiagnosticReports/*Chrome* 2>/dev/null | head -10 || true

  latest=$(ls -t "$HOME"/Library/Logs/DiagnosticReports/*Chrome* 2>/dev/null | head -1 || true)

  if [ -n "${latest:-}" ]; then
    log
    log "Newest crash report:"
    log "$latest"
    log
    log "First 120 lines:"
    sed -n '1,120p' "$latest"

    append_report "- Newest crash report: $latest"
    append_report ""
    append_report '```text'
    sed -n '1,120p' "$latest" >> "$REPORT"
    append_report '```'
  else
    log "No Chrome crash report found."
    append_report "- No Chrome crash report found in ~/Library/Logs/DiagnosticReports."
  fi

  append_report ""
  append_report "Verdict: NO_GO — Chrome app install or macOS/system-level failure likely."
}

chrome_profile_backup_fix() {
  log "=== BACKUP NORMAL CHROME DEFAULT PROFILE ==="
  kill_chrome

  SRC="$HOME/Library/Application Support/Google/Chrome/Default"
  DST="$HOME/Library/Application Support/Google/Chrome/Default.BAK.$(date +%Y%m%d_%H%M%S)"

  if [ ! -d "$SRC" ]; then
    log "Default profile not found: $SRC"
    exit 1
  fi

  mv "$SRC" "$DST"
  log "Moved Default profile to:"
  log "$DST"

  open -a "Google Chrome" http://127.0.0.1:3001
}

chrome_p0_debug() {
  init_report
  repo_check
  chrome_version
  tracker_check || true

  if chrome_clean_profile; then
    log
    log "NEXT ACTION: normal Chrome profile is likely bad."
    log "To isolate it safely, run:"
    log "  ./scripts/hoch_operator_bridge.sh chrome-profile-backup-fix"
    exit 0
  fi

  if chrome_gpu_off; then
    log
    log "NEXT ACTION: disable Chrome hardware acceleration or launch with --disable-gpu."
    exit 0
  fi

  chrome_crash_reports
  log
  log "NEXT ACTION: reinstall Chrome while preserving profile backups."
}

has_health() {
  log "=== HAS HEALTH ==="
  cd "$REPO" || exit 2
  safe_source_tracker_env || true

  if [ -x "./scripts/tracker_healthcheck.sh" ]; then
    ./scripts/tracker_healthcheck.sh
  else
    log "tracker_healthcheck.sh not found or not executable."
  fi

  if [ -f "scripts/pods_final_go_check.py" ]; then
    python3 scripts/pods_final_go_check.py || true
  else
    log "pods_final_go_check.py not found."
  fi
}

case "${1:-help}" in
  repo-check)
    repo_check
    ;;
  tracker-check)
    tracker_check
    ;;
  copy-tracker-password)
    copy_tracker_password
    ;;
  chrome-p0-debug)
    chrome_p0_debug
    ;;
  chrome-clean-profile)
    init_report
    chrome_clean_profile
    ;;
  chrome-gpu-off)
    init_report
    chrome_gpu_off
    ;;
  chrome-crash-reports)
    init_report
    chrome_crash_reports
    ;;
  chrome-profile-backup-fix)
    chrome_profile_backup_fix
    ;;
  has-health)
    has_health
    ;;
  *)
    cat <<EOF
HOCH Operator Bridge

Usage:
  ./scripts/hoch_operator_bridge.sh repo-check
  ./scripts/hoch_operator_bridge.sh tracker-check
  ./scripts/hoch_operator_bridge.sh copy-tracker-password
  ./scripts/hoch_operator_bridge.sh chrome-p0-debug
  ./scripts/hoch_operator_bridge.sh chrome-clean-profile
  ./scripts/hoch_operator_bridge.sh chrome-gpu-off
  ./scripts/hoch_operator_bridge.sh chrome-crash-reports
  ./scripts/hoch_operator_bridge.sh chrome-profile-backup-fix
  ./scripts/hoch_operator_bridge.sh has-health

Start with:
  ./scripts/hoch_operator_bridge.sh chrome-p0-debug
EOF
    ;;
esac
