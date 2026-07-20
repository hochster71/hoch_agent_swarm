#!/bin/zsh
# verify_isolation.sh — fail if Kimi Desktop is registered against HELM monorepo
set -euo pipefail

WS_REG="${HOME}/Library/Application Support/kimi-desktop/kimi-agent/created-workspaces.json"
ALLOWED="${HOME}/Documents/kimi/workspace"
FAIL=0

echo "== Kimi isolation check =="
echo "registry: $WS_REG"
echo "allowed:  $ALLOWED"
echo

if [[ ! -f "$WS_REG" ]]; then
  echo "UNKNOWN: created-workspaces.json missing (Kimi may not be installed)"
  exit 2
fi

echo "--- registry contents ---"
cat "$WS_REG"
echo

# Parse JSON keys only (ignore free-text notes that may mention monorepo by name)
python3 - "$WS_REG" "$ALLOWED" <<'PY'
import json, sys
from pathlib import Path

reg_path = Path(sys.argv[1])
allowed = Path(sys.argv[2]).resolve()
data = json.loads(reg_path.read_text())
if not isinstance(data, dict):
    print("FAIL: registry is not a JSON object")
    sys.exit(1)

keys = [Path(k).expanduser().resolve() for k in data.keys()]
print("--- registered workspace roots ---")
for k in keys:
    print(f"  {k}")

fail = 0
if allowed not in keys:
    print(f"FAIL: allowed workspace not registered: {allowed}")
    fail = 1
else:
    print(f"PASS: allowed workspace present: {allowed}")

forbidden_substrings = (
    "hoch_agent_swarm",
    "/hoch_agent_swarm",
)
for k in keys:
    s = str(k)
    if any(f in s for f in forbidden_substrings):
        print(f"FAIL: monorepo path registered as workspace: {k}")
        fail = 1
    # Also fail if any registered root is outside Documents/kimi (except allowed tree)
    try:
        k.relative_to(Path.home() / "Documents" / "kimi")
        in_kimi = True
    except ValueError:
        in_kimi = False
    if not in_kimi:
        print(f"FAIL: workspace outside ~/Documents/kimi: {k}")
        fail = 1

if fail == 0:
    print("PASS: all registered roots are under ~/Documents/kimi and exclude monorepo")
sys.exit(fail)
PY
PY_RC=$?
if [[ $PY_RC -ne 0 ]]; then
  FAIL=1
fi

# Live process sniff (best-effort): COMMAND name only — avoid matching "kimi" in file paths
echo
echo "--- live Kimi/daimon processes under monorepo (best-effort) ---"
if command -v lsof >/dev/null 2>&1; then
  HITS=$(lsof +D /Users/michaelhoch/hoch_agent_swarm 2>/dev/null \
    | awk 'NR==1 || tolower($1) ~ /kimi|daimon|kimichat/' \
    | head -20 || true)
  # Drop header-only result
  if echo "$HITS" | awk 'NR>1{found=1} END{exit !found}'; then
    echo "$HITS"
    echo "WARN: Kimi-related process may have monorepo files open (review above)"
  else
    echo "PASS: no Kimi/daimon COMMAND hits under monorepo"
  fi
else
  echo "SKIP: lsof not available"
fi

echo
if [[ $FAIL -ne 0 ]]; then
  echo "RESULT: ISOLATION_BREACH"
  exit 1
fi
echo "RESULT: ISOLATION_OK"
exit 0
