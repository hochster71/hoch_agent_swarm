#!/usr/bin/env bash
# audit_stack.sh — unified free auditor for HAS/HASF.
# Runs the $0 open-source audit stack, aggregates results into an evidence artifact,
# and returns PASS/FAIL for the completion-gate framework.
#
# Blocking (fails the gate)  : dependency CVEs (pip-audit), container CRITICAL/HIGH (trivy),
#                              bandit HIGH-severity findings.
# Reporting only (non-block) : ruff style, mypy types, bandit LOW/MED  (bootstrapper defaults;
#                              flip with STRICT=1 to block on those too).
#
# Every tool is optional: if it isn't installed, the step is SKIPPED and noted (never a silent pass).
# Usage:  bash scripts/audit_stack.sh [--mutation]   (mutation testing is slow; opt-in)
set -uo pipefail
cd "$(dirname "$0")/.." || exit 2
ROOT="$(pwd)"; TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUTDIR="docs/evidence/security"; mkdir -p "$OUTDIR"
MD="$OUTDIR/audit_stack_${TS}.md"; JSON="$OUTDIR/audit_stack_${TS}.json"
STRICT="${STRICT:-0}"; RUN_MUTATION=0; [ "${1:-}" = "--mutation" ] && RUN_MUTATION=1
TARGET="backend/brain_convergence backend/final_verifier backend/prompt_registry.py"

FAIL=0; declare -a ROWS
have(){ command -v "$1" >/dev/null 2>&1; }
row(){ ROWS+=("| $1 | $2 | $3 |"); }
block(){ FAIL=1; }

echo "# HAS/HASF Audit Stack — $TS" > "$MD"
echo "" >> "$MD"

echo "== ruff (correctness) =="
if have ruff; then
  if ruff check $TARGET >/tmp/ruff.txt 2>&1; then row "ruff" "PASS" "no lint errors"
  else n=$(grep -c "" /tmp/ruff.txt); row "ruff" "REPORT" "$n lines — see artifact"; [ "$STRICT" = 1 ] && block
    { echo "## ruff"; echo '```'; cat /tmp/ruff.txt; echo '```'; } >> "$MD"; fi
else row "ruff" "SKIP" "not installed (pip install ruff)"; fi

echo "== bandit (python security SAST) =="
if have bandit; then
  bandit -q -r $TARGET -f json -o /tmp/bandit.json >/dev/null 2>&1
  HIGH=$(python3 -c "import json;d=json.load(open('/tmp/bandit.json'));print(sum(1 for r in d.get('results',[]) if r['issue_severity']=='HIGH'))" 2>/dev/null||echo 0)
  TOT=$(python3 -c "import json;print(len(json.load(open('/tmp/bandit.json')).get('results',[])))" 2>/dev/null||echo 0)
  if [ "$HIGH" -gt 0 ]; then row "bandit" "FAIL" "$HIGH HIGH / $TOT total"; block
  else row "bandit" "REPORT" "0 HIGH / $TOT total"; fi
else row "bandit" "SKIP" "not installed (pip install bandit)"; fi

echo "== pip-audit (dependency CVEs) =="
if have pip-audit; then
  if pip-audit --progress-spinner off >/tmp/pipaudit.txt 2>&1; then row "pip-audit" "PASS" "no known CVEs"
  else n=$(grep -ciE "GHSA-|CVE-|PYSEC-" /tmp/pipaudit.txt); n=${n:-0}; row "pip-audit" "FAIL" "$n dependency CVEs"; block
    { echo "## pip-audit"; echo '```'; tail -40 /tmp/pipaudit.txt; echo '```'; } >> "$MD"; fi
else row "pip-audit" "SKIP" "not installed (pip install pip-audit)"; fi

echo "== npm audit (frontend deps, with accepted-risk allowlist) =="
if have npm && [ -f frontend/package.json ]; then
  ( cd frontend && npm audit --json >/tmp/npmaudit.json 2>/dev/null ) || true
  if python3 scripts/npm_audit_gate.py /tmp/npmaudit.json config/security_accepted_risks.json >/tmp/npmgate.txt 2>&1; then
    row "npm-audit" "PASS" "$(cat /tmp/npmgate.txt)"
  else
    row "npm-audit" "FAIL" "$(cat /tmp/npmgate.txt)"; block
    { echo "## npm-audit"; echo '```'; cat /tmp/npmgate.txt; echo '```'; } >> "$MD"
  fi
else row "npm-audit" "SKIP" "npm or frontend/package.json missing"; fi

echo "== trivy (container / fs / IaC) =="
if have trivy; then
  if trivy fs --scanners vuln --severity CRITICAL,HIGH --quiet --exit-code 1 . >/tmp/trivy.txt 2>&1; then row "trivy" "PASS" "no CRITICAL/HIGH"
  else row "trivy" "FAIL" "CRITICAL/HIGH found"; block
    { echo "## trivy"; echo '```'; tail -40 /tmp/trivy.txt; echo '```'; } >> "$MD"; fi
else row "trivy" "SKIP" "not installed (brew install trivy / apt)"; fi

echo "== mypy (types, report-only) =="
if have mypy; then
  mypy $TARGET >/tmp/mypy.txt 2>&1 && row "mypy" "PASS" "no type errors" || row "mypy" "REPORT" "type findings — see artifact"
else row "mypy" "SKIP" "not installed (pip install mypy)"; fi

if [ "$RUN_MUTATION" = 1 ] && have mutmut; then
  echo "== mutmut (mutation testing — do the tests bite?) =="
  mutmut run >/tmp/mut.txt 2>&1 || true
  row "mutmut" "REPORT" "see artifact (survivors = weak tests)"
  { echo "## mutmut"; echo '```'; tail -20 /tmp/mut.txt; echo '```'; } >> "$MD"
fi

# ---- aggregate ----
VERDICT=$([ "$FAIL" = 0 ] && echo PASS || echo FAIL)
{
  echo "## Summary — VERDICT: **$VERDICT**"; echo ""
  echo "| Tool | Result | Detail |"; echo "|---|---|---|"
  printf '%s\n' "${ROWS[@]}"
  echo ""; echo "_Blocking on: dependency CVEs, container CRITICAL/HIGH, bandit HIGH. STRICT=$STRICT._"
} >> "$MD"
python3 - "$JSON" "$VERDICT" "$TS" <<'PY'
import json,sys
json.dump({"verdict":sys.argv[2],"timestamp":sys.argv[3],"schema":"has-audit-stack-v1"}, open(sys.argv[1],"w"), indent=2)
PY
echo ""; echo "AUDIT_STACK VERDICT=$VERDICT  evidence=$MD"
[ "$VERDICT" = PASS ] && exit 0 || exit 1
