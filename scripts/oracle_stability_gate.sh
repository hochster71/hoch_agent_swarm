#!/usr/bin/env bash
#
#   PURPOSE: QUIESCENCE VERIFICATION
#   NOT:     SNAPSHOT COHERENCE
#
# FOUNDER DECISION 2026-07-20: live oracles use SNAPSHOT_COPY. Under that policy the
# promotion gate is CAPTURE COHERENCE (scripts/oracle_snapshot.py:
# source_sha256_at_capture == snapshot_sha256), NOT long-term source stability.
#
# This gate is therefore NOT mandatory for promotion today. It applies only if policy
# changes to QUIESCED_SNAPSHOT. Do not treat a pass here as a promotion prerequisite,
# and do not treat its absence as a promotion blocker.
# oracle_stability_gate.sh — prove an oracle is quiesced before promotion verification.
#
# FOUNDER DECISION 2026-07-20: promotion verification uses QUIESCED SNAPSHOT mode.
# Byte identity is pinned; freshness windows are for RUNTIME HEALTH only. Mixing the two
# reintroduces the ambiguity this replaces.
#
# WHY THE WINDOW MATTERS MORE THAN THE SAMPLES
# --------------------------------------------
# A short window produces false confidence. build_to_goal_status.json showed three
# distinct hashes inside ~15 minutes on 2026-07-20 — a cycle of minutes. A 2-second
# two-sample check would have passed ~99% of the time while proving nothing.
#
# So this gate REFUSES to certify unless the observation window exceeds a DECLARED
# writer period. If the period is unknown, the gate reports UNKNOWN — it can detect
# instability, but it cannot prove quiescence against an unknown cycle.
#
# Usage:
#   scripts/oracle_stability_gate.sh --period-seconds <N> <path> [<path>...]
#   scripts/oracle_stability_gate.sh --writer-stopped   <path> [<path>...]
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

PERIOD=""; STOPPED=0
while [[ "${1:-}" == --* ]]; do
  case "$1" in
    --period-seconds) PERIOD="$2"; shift 2 ;;
    --writer-stopped) STOPPED=1; shift ;;
    *) echo "unknown flag $1" >&2; exit 2 ;;
  esac
done
[[ $# -gt 0 ]] || { echo "FAIL: no oracle paths given" >&2; exit 2; }

if [[ $STOPPED -eq 0 && -z "$PERIOD" ]]; then
  echo "UNKNOWN: no writer period declared and writer not confirmed stopped." >&2
  echo "  A stability sample cannot prove quiescence against an unknown cycle." >&2
  echo "  Supply --period-seconds <N>, or stop the writer and pass --writer-stopped." >&2
  exit 3
fi

# Window must exceed the writer period, with margin, so a sample cannot fall between writes.
WINDOW=${PERIOD:+$(( PERIOD * 2 + 5 ))}; WINDOW=${WINDOW:-10}
echo "observation window: ${WINDOW}s (declared period: ${PERIOD:-writer-stopped})"

fail=0
for f in "$@"; do
  [[ -f "$f" ]] || { echo "FAIL $f: absent"; fail=1; continue; }
  a=$(sha256sum "$f" | cut -d' ' -f1)
  sleep "$WINDOW"
  b=$(sha256sum "$f" | cut -d' ' -f1)
  if [[ "$a" == "$b" ]]; then
    echo "STABLE   $f"
    echo "         $a"
  else
    echo "UNSTABLE $f — writer active during the window; cannot pin bytes"
    echo "         $a"
    echo "         $b"
    fail=1
  fi
done
[[ $fail -eq 0 ]] || { echo "GATE FAILED — do not capture promotion evidence" >&2; exit 1; }
echo "GATE PASSED — bytes stable across the window; safe to pin"
