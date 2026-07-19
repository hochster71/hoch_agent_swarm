#!/usr/bin/env bash
set -u

ROOT="${HELM_ROOT:-$HOME/hoch_agent_swarm}"
REFRESH="${HELM_REFRESH_SECONDS:-2}"

BUS="$ROOT/coordination/coordination_bus.json"
QUEUE="$ROOT/has_live_project_tracker/data/helm_task_queue.json"
HAF="$ROOT/coordination/audit_factory/runs/latest/audit_status.json"
LOCK="$ROOT/data/runtime/voice_command_audit.lock"

cleanup() {
  printf '\033[?25h\033[0m\n'
}
trap cleanup EXIT INT TERM

command -v jq >/dev/null 2>&1 || {
  echo "HELM requires jq. Install with: brew install jq"
  exit 1
}

read_json() {
  local file="$1"
  local query="$2"
  local fallback="${3:-UNKNOWN}"

  if [[ -r "$file" ]]; then
    jq -r "$query // \"$fallback\"" "$file" 2>/dev/null || printf '%s' "$fallback"
  else
    printf '%s' "$fallback"
  fi
}

state_color() {
  case "${1^^}" in
    LIVE|ONLINE|ACTIVE|PASS|GO|COMPLETE|COMPLETED|CONFIRMED_LIVE)
      printf '\033[1;32m'
      ;;
    HOLD|BLOCKED|DEGRADED|STALE|PASS_CANDIDATE|PENDING)
      printf '\033[1;33m'
      ;;
    FAIL|FAILED|ERROR|OFFLINE)
      printf '\033[1;31m'
      ;;
    *)
      printf '\033[1;90m'
      ;;
  esac
}

print_state() {
  local label="$1"
  local value="$2"
  local color
  color="$(state_color "$value")"
  printf "  %-24s ${color}%-22s\033[0m\n" "$label" "$value"
}

printf '\033[?25l'

while true; do
  now="$(date '+%Y-%m-%d %H:%M:%S %Z')"
  uptime="$(uptime | sed 's/.*up //' | sed 's/, [0-9]* user.*//')"

  run_id="$(read_json "$BUS" '.active_run_id // .run_id')"
  bus_state="$(read_json "$BUS" '.status // .runtime_status')"
  cycle="$(read_json "$BUS" '.cycle // .current_cycle' '0')"

  queue_total="$(read_json "$QUEUE" 'if type=="array" then length else (.tasks | length) end' '0')"
  running="$(read_json "$QUEUE" '[.. | objects | select((.status? // "") == "RUNNING")] | length' '0')"
  blocked="$(read_json "$QUEUE" '[.. | objects | select((.status? // "") == "BLOCKED")] | length' '0')"

  haf_decision="$(read_json "$HAF" '.decision // .status')"
  haf_pass="$(read_json "$HAF" '.summary.pass // .pass_count' '0')"
  haf_candidate="$(read_json "$HAF" '.summary.pass_candidate // .pass_candidate_count' '0')"
  haf_hold="$(read_json "$HAF" '.summary.hold // .hold_count' '0')"
  haf_fail="$(read_json "$HAF" '.summary.fail // .fail_count' '0')"

  git_sha="$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || printf 'UNKNOWN')"

  if git -C "$ROOT" diff --quiet --ignore-submodules HEAD -- 2>/dev/null &&
     [[ -z "$(git -C "$ROOT" status --porcelain 2>/dev/null)" ]]; then
    git_tree="CLEAN"
  else
    git_tree="DIRTY"
  fi

  relay_state="UNKNOWN"
  if curl -kfsS --connect-timeout 2 \
      "https://hoch-relay-001.tail826763.ts.net:3012/api/registry" \
      >/dev/null 2>&1; then
    relay_state="ONLINE"
  fi

  printf '\033[H\033[2J'
  cat <<'EOF'
██╗  ██╗███████╗██╗     ███╗   ███╗
██║  ██║██╔════╝██║     ████╗ ████║
███████║█████╗  ██║     ██╔████╔██║
██╔══██║██╔══╝  ██║     ██║╚██╔╝██║
██║  ██║███████╗███████╗██║ ╚═╝ ██║
╚═╝  ╚═╝╚══════╝╚══════╝╚═╝     ╚═╝
       HOCH EXECUTION & LIFECYCLE MANAGER
EOF

  printf "\n  %s\n" "$now"
  printf "  Host uptime: %s\n" "$uptime"
  printf "══════════════════════════════════════════════════════════════════\n"

  printf "\nRUNTIME TRUTH\n"
  print_state "Coordination Bus" "$bus_state"
  print_state "Factory-Verse Relay" "$relay_state"
  print_state "Production Authority" "HOLD"
  print_state "Truth Doctrine" "NO FAKE GREEN"

  printf "\nEXECUTION\n"
  printf "  %-24s %-22s\n" "Active Run" "$run_id"
  printf "  %-24s %-22s\n" "Governed Cycle" "$cycle"
  printf "  %-24s %-22s\n" "Queued Tasks" "$queue_total"
  printf "  %-24s %-22s\n" "Running Tasks" "$running"
  printf "  %-24s %-22s\n" "Blocked Tasks" "$blocked"

  printf "\nHAF / SECURITY\n"
  print_state "Assessment Decision" "$haf_decision"
  printf "  PASS %-4s  CANDIDATE %-4s  HOLD %-4s  FAIL %-4s\n" \
    "$haf_pass" "$haf_candidate" "$haf_hold" "$haf_fail"
  printf "  %-24s %-22s\n" "Audit Lock" \
    "$([[ -e "$LOCK" ]] && printf PRESENT || printf AVAILABLE)"

  printf "\nSOURCE CONTROL\n"
  printf "  %-24s %-22s\n" "HEAD" "$git_sha"
  print_state "Working Tree" "$git_tree"
  print_state "Remote Verification" "PENDING"

  printf "\n══════════════════════════════════════════════════════════════════\n"
  printf " Refresh: %ss  |  Ctrl-C closes viewer; HELM services continue.\n" "$REFRESH"

  sleep "$REFRESH"
done
