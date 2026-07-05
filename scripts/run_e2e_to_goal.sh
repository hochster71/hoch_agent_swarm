#!/usr/bin/env bash
# run_e2e_to_goal.sh — one command that runs the whole verification chain to GOAL and
# produces the evidence-backed Go/No-Go packet. Each stage is resilient: a missing tool is
# SKIPPED and noted (never a silent pass). Exit 0 only if the final Go/No-Go verdict is GO.
#
#   Stage 1  audit stack     — free security/correctness (ruff/bandit/pip-audit/npm/trivy)
#   Stage 2  brain tests     — convergence loop + guards (harvest/splits/scorer/judge-audit)
#   Stage 3  M0 generation   — run one convergence generation, write champion + evidence
#   Stage 4  Go/No-Go        — score the 10 GOAL criteria, emit the release packet
#
# Usage:  bash scripts/run_e2e_to_goal.sh
set -uo pipefail
cd "$(dirname "$0")/.." || exit 2
export PATH="$HOME/.local/bin:$PATH"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
PY="$( [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3 )"
declare -a SUMMARY; STAGE_FAIL=0
line(){ echo "──────────────────────────────────────────────"; }
mark(){ SUMMARY+=("$1"); }

line; echo "  HAS/HASF — E2E RUN TO GOAL  ($TS)"; echo "  python: $PY"; line

echo ">> Stage 1/4 : audit stack (free security + correctness)"
if bash scripts/audit_stack.sh; then mark "1 audit-stack   : PASS"
else mark "1 audit-stack   : FAIL (see docs/evidence/security/)"; STAGE_FAIL=1; fi
line

echo ">> Stage 2/4 : BRAIN convergence tests"
if $PY -m pytest tests/integration/test_brain_convergence_harvest.py \
        tests/integration/test_brain_convergence_guards.py \
        tests/integration/test_brain_convergence_m0_full.py -q; then mark "2 brain-tests    : PASS"
else mark "2 brain-tests    : FAIL"; STAGE_FAIL=1; fi
line

echo ">> Stage 3/4 : M0 convergence generation (harvest→split→audit→score→promote→converge)"
if $PY -m backend.brain_convergence.run_m0 | tail -1; then mark "3 M0-generation  : PASS"
else mark "3 M0-generation  : FAIL"; STAGE_FAIL=1; fi
line

echo ">> Stage 4/4 : Release Go/No-Go (10 GOAL criteria)"
GO_OUT="$($PY scripts/release_go_no_go.py 2>&1)"; GO_RC=$?
echo "$GO_OUT" | grep -E "VERDICT|Blockers"
if [ $GO_RC -eq 0 ]; then mark "4 go-no-go       : GO (10/10 VERIFIED)"
else mark "4 go-no-go       : NO-GO — $(echo "$GO_OUT" | grep -oE 'Blockers to GO:.*')"; STAGE_FAIL=1; fi
line

echo "  E2E SUMMARY"
printf '   %s\n' "${SUMMARY[@]}"
line
if [ $STAGE_FAIL -eq 0 ]; then
  echo "  ✅ E2E VERDICT: GO — every stage green. GOAL is technically VERIFIED."
  echo "     Remaining: operator signs production_go_status via the release-authority path."
  exit 0
else
  echo "  ⛔ E2E VERDICT: NO-GO — one or more stages failed. See evidence above; nothing to sign yet."
  exit 1
fi
