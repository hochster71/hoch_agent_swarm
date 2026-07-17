#!/usr/bin/env bash
# =============================================================================
# activate_always_current.sh — flip the HELM "always-current UI" system live.
#
# ONE idempotent, soak-interlocked activator. Run it ONCE, AFTER the 24h Phase C
# soak has SEALED (~2:45pm CT). It ties together the three pieces built this
# session:
#   * backend/runtime_freshness.py        — the freshness scoreboard (read-only)
#   * backend/runtime_freshness_api.py     — FastAPI router -> GET /api/v1/helm/freshness
#   * scripts/runtime_refresher.py + deploy/launchd/com.hoch.runtime.refresher.plist
#                                          — the continuous refresher (COMPUTED signals)
#
# WIRING FACTS (cited from the live repo, 2026-07-16):
#   * The app that OWNS /api/v1/helm/* is  backend/helm_live_api.py  (app = FastAPI
#     "HELM LIVE"). Every /api/v1/helm/{wall,runtime,factories,tasks,...} route is
#     defined there. backend/main.py (:8000) does NOT own these routes, so the
#     freshness router goes into helm_live_api.py.
#   * That app is served by uvicorn `backend.helm_live_api:app` on :8770, kept alive
#     by the HARDENED AUTOLOOP  scripts/helm_autoloop.sh, launchd label
#     `com.hoch.helm-autoloop`. The older launcher run_helm_live_foreground.sh
#     (label `com.hoch.helm.voice`) self-declares RETIRED/disabled. This script
#     detects which one is actually live and reloads THAT one only.
#   * The autoloop starts uvicorn WITHOUT --reload, so a code change requires the
#     serving process to be restarted (handled below, API service only).
#
# NO FAKE GREEN: the continuous refresher only re-derives COMPUTED signals
# (control_plane, goal_state, mission_state). The LIVENESS signals
# (supervisor_heartbeat, helm_runtime_state, helm_agent_registry),
# orchestration_authority, and runtime_truth_snapshot are produced elsewhere; this
# script never fabricates them. If their producer is down, the board stays STALE
# honestly and this script exits non-zero naming each owed producer.
#
# USAGE:
#   bash scripts/activate_always_current.sh            # activate (run after seal)
#   bash scripts/activate_always_current.sh --dry-run  # read-only preview, changes nothing
# =============================================================================
set -euo pipefail

# --- resolve repo root from this script's location (robust to cwd) -----------
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" || "${1:-}" == "-n" ]]; then DRY_RUN=1; fi

UID_NUM="$(id -u)"
LA_DIR="$HOME/Library/LaunchAgents"

LABEL_REFRESHER="com.hoch.runtime.refresher"
PLIST_SRC="$ROOT/deploy/launchd/com.hoch.runtime.refresher.plist"
PLIST_DST="$LA_DIR/com.hoch.runtime.refresher.plist"

API_FILE="$ROOT/backend/helm_live_api.py"
API_PORT="8770"
LABEL_AUTOLOOP="com.hoch.helm-autoloop"   # live supervisor of helm_live_api:app (:8770)
LABEL_VOICE="com.hoch.helm.voice"          # retired/disabled alternative launcher

say()  { printf '%s\n' "$*"; }
hr()   { printf '%s\n' "------------------------------------------------------------------------"; }
head_() { hr; printf '%s\n' "$*"; hr; }
act()  { # echo an irreversible action, then run it (unless dry-run)
  printf '  [ACT] %s\n' "$*"
  if [[ "$DRY_RUN" -eq 1 ]]; then printf '        (dry-run: not executed)\n'; return 0; fi
  eval "$@"
}

label_loaded() { launchctl list 2>/dev/null | awk '{print $3}' | grep -qx "$1"; }

# =============================================================================
# 0. HARD INTERLOCK — refuse to run while ANY soak is alive.
# =============================================================================
head_ "0. SOAK INTERLOCK"
if pgrep -f 'soak_runner.py' >/dev/null 2>&1; then
  say "ABORT: soak still active — activation must run after seal"
  exit 3
fi
say "  OK: no soak_runner.py process found — clear to activate."
[[ "$DRY_RUN" -eq 1 ]] && say "  MODE: --dry-run (read-only preview; no changes will be made)."

# =============================================================================
# STEP A — load the continuous refresher (COMPUTED-signal freshness engine).
# =============================================================================
head_ "STEP A. Continuous refresher -> launchd ($LABEL_REFRESHER)"
if [[ ! -f "$PLIST_SRC" ]]; then
  say "  ERROR: staged plist missing: $PLIST_SRC"; exit 1
fi
# RunAtLoad sanity (so we know it starts immediately on load).
if grep -q "<key>RunAtLoad</key>" "$PLIST_SRC" && \
   grep -A1 "<key>RunAtLoad</key>" "$PLIST_SRC" | grep -q "<true/>"; then
  say "  verified: plist has RunAtLoad=true (starts on load)."
else
  say "  WARNING: plist does not declare RunAtLoad=true — it will not start until StartInterval."
fi
act "mkdir -p '$LA_DIR'"
act "cp '$PLIST_SRC' '$PLIST_DST'"
# Idempotent: unload if already registered, then load -w (enables the label).
if label_loaded "$LABEL_REFRESHER"; then
  say "  refresher already loaded — unloading first for a clean idempotent re-load."
  act "launchctl unload '$PLIST_DST' 2>/dev/null || true"
fi
act "launchctl load -w '$PLIST_DST'"
# Verify registration.
if [[ "$DRY_RUN" -eq 0 ]]; then
  if label_loaded "$LABEL_REFRESHER"; then
    say "  OK: $LABEL_REFRESHER is registered with launchd."
  else
    say "  ERROR: $LABEL_REFRESHER did NOT register — check $LA_DIR and launchctl error output."
    exit 1
  fi
else
  say "  (dry-run) would verify $LABEL_REFRESHER registered."
fi

# =============================================================================
# STEP B — wire GET /api/v1/helm/freshness into the app that owns /api/v1/helm/*,
#          then graceful-reload ONLY that API service.
# =============================================================================
head_ "STEP B. Wire /api/v1/helm/freshness into backend/helm_live_api.py"
if [[ ! -f "$API_FILE" ]]; then say "  ERROR: $API_FILE not found"; exit 1; fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  if grep -q "runtime_freshness_api" "$API_FILE"; then
    say "  (dry-run) freshness route ALREADY wired — no edit needed."
    WIRE_CHANGED=0
  else
    say "  (dry-run) WOULD add after the voice_router include:"
    say "            from backend.runtime_freshness_api import router as freshness_router"
    say "            app.include_router(freshness_router)"
    WIRE_CHANGED=1
  fi
else
  WIRE_CHANGED="$(python3 - "$API_FILE" <<'PY'
import sys
p = sys.argv[1]
src = open(p, encoding="utf-8").read()
if "runtime_freshness_api" in src:
    print("0")  # already wired
    sys.exit(0)
anchor = ("from backend.voice.router import router as voice_router\n"
          "app.include_router(voice_router)")
if anchor not in src:
    sys.stderr.write("ANCHOR_NOT_FOUND")
    print("ERR")
    sys.exit(2)
addition = (anchor + "\n\n"
            "# ALWAYS-CURRENT: honest runtime-freshness board -> GET /api/v1/helm/freshness\n"
            "from backend.runtime_freshness_api import router as freshness_router\n"
            "app.include_router(freshness_router)")
open(p, "w", encoding="utf-8").write(src.replace(anchor, addition, 1))
print("1")  # changed
PY
)" || { say "  ERROR: could not locate the voice_router include anchor in $API_FILE — not edited."; exit 1; }
  case "$WIRE_CHANGED" in
    0) say "  freshness route already present — no change (idempotent)." ;;
    1) say "  freshness route ADDED after the voice_router include." ;;
    *) say "  ERROR: unexpected wiring result '$WIRE_CHANGED'"; exit 1 ;;
  esac
fi

# --- reload the serving API so the new route is live -------------------------
say "  Detecting which launchd job serves helm_live_api:app on :$API_PORT ..."
SERVED_BY="none"
if label_loaded "$LABEL_VOICE"; then SERVED_BY="$LABEL_VOICE"; fi
if label_loaded "$LABEL_AUTOLOOP"; then SERVED_BY="$LABEL_AUTOLOOP"; fi   # autoloop wins (live supervisor)
say "  serving job: $SERVED_BY"

if [[ "$WIRE_CHANGED" == "1" ]]; then
  if [[ "$SERVED_BY" == "$LABEL_VOICE" ]]; then
    # This job execs uvicorn directly -> kickstart -k reloads the code.
    act "launchctl kickstart -k 'gui/${UID_NUM}/${LABEL_VOICE}'"
  elif [[ "$SERVED_BY" == "$LABEL_AUTOLOOP" ]]; then
    # Autoloop keeps uvicorn up by polling; kill the :$API_PORT listener so the
    # autoloop respawns it WITH the new code, then kick the autoloop to respawn fast.
    say "  autoloop model: stopping the :$API_PORT uvicorn listener so it respawns with new code."
    if command -v lsof >/dev/null 2>&1; then
      PIDS="$(lsof -nP -iTCP:"$API_PORT" -sTCP:LISTEN -t 2>/dev/null | sort -u || true)"
      if [[ -n "$PIDS" ]]; then
        # shellcheck disable=SC2086
        act "kill $PIDS 2>/dev/null || true"
      else
        say "  (no current listener on :$API_PORT — autoloop will start it fresh)"
      fi
    else
      say "  WARNING: lsof not available — relying on kickstart of the autoloop to cycle the API."
    fi
    act "launchctl kickstart -k 'gui/${UID_NUM}/${LABEL_AUTOLOOP}' 2>/dev/null || true"
  else
    say "  NOTE: no live helm_live_api launchd job detected. FOUNDER STEP: restart the"
    say "        helm_live_api:app service (:$API_PORT) so GET /api/v1/helm/freshness is served."
  fi
else
  say "  route unchanged -> no API reload required."
fi

# --- verify the endpoint answers (self-signed TLS on :8770 -> curl -k) -------
if [[ "$DRY_RUN" -eq 0 && "$SERVED_BY" != "none" ]]; then
  say "  polling GET /api/v1/helm/freshness (up to ~40s for respawn) ..."
  OK_EP=0
  for _ in $(seq 1 20); do
    for scheme in https http; do
      code="$(curl -fsSk -o /dev/null -w '%{http_code}' --max-time 4 \
        "${scheme}://127.0.0.1:${API_PORT}/api/v1/helm/freshness" 2>/dev/null || echo "000")"
      if [[ "$code" == "200" ]]; then
        say "  OK: ${scheme}://127.0.0.1:${API_PORT}/api/v1/helm/freshness -> 200"
        OK_EP=1; break
      fi
    done
    [[ "$OK_EP" -eq 1 ]] && break
    sleep 2
  done
  [[ "$OK_EP" -eq 0 ]] && say "  WARNING: endpoint not yet 200 — the autoloop may still be respawning; re-check shortly."
fi

# =============================================================================
# STEP C — producers for the signals the refresher DOES NOT (and must not) touch.
# =============================================================================
head_ "STEP C. Liveness / non-computed producers (honest — no fabrication)"
say "  The continuous refresher (Step A) keeps ONLY the COMPUTED signals current:"
say "    control_plane, goal_state, mission_state  (re-derived by their real regenerators)."
say ""
say "  The following are produced ELSEWHERE and are DELIBERATELY not auto-refreshed"
say "  (writing them from here would be fake liveness). No on-disk launchd plist in this"
say "  repo owns them, so this script does NOT start them — it reports the exact producer:"
say ""

# supervisor_heartbeat <- backend/mission_control/helm_supervisor.py
if pgrep -f 'helm_supervisor' >/dev/null 2>&1; then
  say "    [running]  supervisor_heartbeat  <- backend/mission_control/helm_supervisor.py (pgrep hit)"
else
  say "    [DOWN]     supervisor_heartbeat  <- backend/mission_control/helm_supervisor.py"
  say "               FOUNDER STEP: start the HELM supervisor so it stamps"
  say "               has_live_project_tracker/data/helm_supervisor_heartbeat.json."
fi

# helm_runtime_state + helm_agent_registry <- scripts/helm_autonomy_runner.py (runtime loop / dispatchers)
if pgrep -f 'helm_autonomy_runner' >/dev/null 2>&1; then
  say "    [running]  helm_runtime_state / helm_agent_registry <- scripts/helm_autonomy_runner.py (pgrep hit)"
else
  say "    [DOWN]     helm_runtime_state / helm_agent_registry <- scripts/helm_autonomy_runner.py"
  say "               (registry is written by runtime dispatchers; no safe read-only regenerator)."
  say "               FOUNDER STEP: start the HELM runtime loop / autonomy runner so these stamp."
  say "               HOCH_STATUS.md lists 'com.hoch.goal.runtime.loop — goal runtime' as the"
  say "               runtime-loop job; this script will NOT guess-start it (no fake green)."
fi

say ""
say "    orchestration_authority  <- secure_sync (HOCH-200 authority; remote/founder-owned, not local)."
say "    runtime_truth_snapshot   <- the live soak; POST-SEAL this is frozen and SHOULD read stale (honest)."

# =============================================================================
# VERIFY — print the real freshness board and gate on OVERALL.
# =============================================================================
head_ "VERIFY. HELM runtime freshness board"
if [[ "$DRY_RUN" -eq 1 ]]; then
  say "  (dry-run) would run: python3 -m backend.runtime_freshness"
  say "  (dry-run) preview only — showing current board below for reference:"
fi
BOARD="$(cd "$ROOT" && python3 -m backend.runtime_freshness 2>&1)" || {
  say "  ERROR: freshness board failed to run:"; printf '%s\n' "$BOARD"; exit 1; }
printf '%s\n' "$BOARD"
hr

OVERALL="$(printf '%s\n' "$BOARD" | awk '/^OVERALL:/{print $2; exit}')"
say "OVERALL = ${OVERALL:-UNKNOWN}"

if [[ "$DRY_RUN" -eq 1 ]]; then
  say ""
  say "DRY-RUN complete — no changes were made. Re-run without --dry-run after the seal to activate."
  exit 0
fi

if [[ "$OVERALL" == "FRESH" ]]; then
  say ""
  say "ACTIVATION COMPLETE: always-current UI is live and every signal is within budget."
  exit 0
fi

# Non-FRESH: name each remaining signal and its owed producer. NO FAKE GREEN.
say ""
say "ACTIVATION PARTIAL: OVERALL is $OVERALL — the following signals are NOT fresh."
say "The always-current PLUMBING is live (route + refresher), but these signals owe a producer:"
printf '%s\n' "$BOARD" | grep -E '^\[STALE\]|^\[UNKNOWN\]' | while IFS= read -r line; do
  sig="$(printf '%s' "$line" | awk '{print $2}')"
  case "$sig" in
    control_plane|goal_state|mission_state)
      owed="COMPUTED — the refresher ($LABEL_REFRESHER) regenerates it; give it one cycle then re-run." ;;
    supervisor_heartbeat)
      owed="backend/mission_control/helm_supervisor.py (HELM supervisor must be running)." ;;
    helm_runtime_state|helm_agent_registry)
      owed="scripts/helm_autonomy_runner.py (HELM runtime loop / dispatchers must be running)." ;;
    orchestration_authority)
      owed="secure_sync from HOCH-200 (remote authority; founder-owned)." ;;
    runtime_truth_snapshot)
      owed="the live soak (frozen post-seal -> honestly stale; expected)." ;;
    *)
      owed="see backend/runtime_freshness.py SIGNAL_SPECS for its source." ;;
  esac
  printf '  - %-24s owed by: %s\n' "$sig" "$owed"
done
say ""
say "Fix the owed producers above (founder-owned where noted), then re-run this script — it is idempotent."
exit 4
