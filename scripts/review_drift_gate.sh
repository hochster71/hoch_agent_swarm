#!/usr/bin/env bash
# review_drift_gate.sh — three-class drift evaluation for a pinned review.
#
# FOUNDER CORRECTION 2026-07-20. The prior version treated ALL drift as destroying the
# review. That was wrong: git commit objects are IMMUTABLE, so findings about an exact SHA
# survive a concurrent commit. What a concurrent commit destroys is the candidate's
# standing as current HEAD / promotion candidate — not the truth of the review.
#
#   CLASS A — CANDIDATE-BYTE INVALIDATION  (the reviewed bytes themselves moved)
#       review worktree HEAD changed | worktree dirty | snapshot bytes differ
#       -> REVIEW_INVALIDATED                                          exit 1
#
#   CLASS B — PROMOTION-BINDING DRIFT  (the world moved around a still-valid review)
#       branch HEAD | remote ref | register.recorded_head | target branch | lease expiry
#       -> PROMOTION_BINDING_STALE / REVIEW_REMAINS_VALID_FOR_PINNED_SHA   exit 2
#
#   CLASS C — REVIEW ENVIRONMENT UNAVAILABLE  (execution dependency missing; no byte drift proven)
#       configured review path absent | mount unavailable | git-dir unresolved | snapshots missing
#       -> REVIEW_ENVIRONMENT_UNAVAILABLE                              exit 3
#
# Exit 0 = both intact. Class C dominates preflight; Class A dominates when both A and B are present.
set -uo pipefail
cd "$(git rev-parse --show-toplevel)"
L=coordination/governance/review_lease.json
W=.helm_worktrees/proc-001
r(){ printf '  %-36s %s\n' "$1" "$2"; }

# Preflight: Class C Checks
if [ ! -f "$L" ]; then
  echo "REVIEW DRIFT GATE — NO LEASE"
  echo "REVIEW_ENVIRONMENT_UNAVAILABLE"
  echo "LEASE_UNREADABLE_OR_INVALID"
  echo "NO_BYTE_DRIFT_PROVEN"
  exit 3
fi

PARSE_OUT=$(python3 - <<'PYEOF'
import json, sys, datetime
try:
    with open('coordination/governance/review_lease.json') as f:
        data = json.load(f)
    for k in ["base_head", "lease_id", "expires_at", "pinned_snapshots"]:
        assert k in data, f"missing key: {k}"
    assert isinstance(data["pinned_snapshots"], dict), "pinned_snapshots not dict"
    
    expires_str = data["expires_at"]
    if expires_str.endswith('Z'):
        expires_str = expires_str[:-1] + '+00:00'
    expires_dt = datetime.datetime.fromisoformat(expires_str)
    now_dt = datetime.datetime.now(datetime.timezone.utc)
    
    expired = now_dt >= expires_dt
    print(data["base_head"])
    print(data.get("target_branch", ""))
    print("EXPIRED" if expired else "OK")
    sys.exit(0)
except Exception as e:
    print(f"PARSE_ERROR: {e}", file=sys.stderr)
    sys.exit(3)
PYEOF
)

if [ $? -ne 0 ]; then
  echo "REVIEW DRIFT GATE — LEASE PARSE FAILURE"
  echo "REVIEW_ENVIRONMENT_UNAVAILABLE"
  echo "LEASE_UNREADABLE_OR_INVALID"
  echo "NO_BYTE_DRIFT_PROVEN"
  exit 3
fi

# Read values from PARSE_OUT
B=$(echo "$PARSE_OUT" | sed -n '1p')
target_branch=$(echo "$PARSE_OUT" | sed -n '2p')
expiry_status=$(echo "$PARSE_OUT" | sed -n '3p')

echo "REVIEW DRIFT GATE — $(python3 -c "import json;print(json.load(open('$L'))['lease_id'])")"

echo "PREFLIGHT — Remote branch query"
remote_head=""
if [ -n "$target_branch" ]; then
  remote_head=$(GIT_TERMINAL_PROMPT=0 GIT_ASKPASS=/bin/true git ls-remote github "refs/heads/$target_branch" 2>/dev/null | awk '{print $1}')
  if [ -z "$remote_head" ]; then
    r "remote ref ($target_branch)" "UNAVAILABLE"
    echo
    echo "REVIEW_ENVIRONMENT_UNAVAILABLE"
    echo "REMOTE_BINDING_UNAVAILABLE"
    echo "NO_REMOTE_DRIFT_PROVEN"
    exit 3
  fi
  r "remote ref ($target_branch)" "RESOLVED"
fi

C_ERR=0
echo "PREFLIGHT — Environment check"
if [ ! -d "$W" ]; then
  r "review worktree directory" "MISSING ($W)"
  C_ERR=1
else
  r "review worktree directory" "EXISTS"
fi

if [ ! -f "$W/.git" ] && [ ! -d "$W/.git" ]; then
  r "review worktree .git" "MISSING"
  C_ERR=1
else
  r "review worktree .git" "EXISTS"
fi

wh=""
if [ $C_ERR -eq 0 ]; then
  wh=$(git -C $W rev-parse HEAD 2>/dev/null)
  if [ $? -ne 0 ] || [ -z "$wh" ]; then
    r "review worktree git-dir" "UNRESOLVED / git command failed"
    C_ERR=1
  else
    r "review worktree git-dir" "RESOLVABLE"
  fi
fi

# Check for snapshot file presence on the review worktree
while read -r want path; do
  if [ ! -f "$W/$path" ]; then
    r "snapshot $(basename $path)" "MISSING in worktree ($W/$path)"
    C_ERR=1
  fi
done < <(python3 -c "import json;d=json.load(open('$L'));[print(v,k) for k,v in d['pinned_snapshots'].items()]")

if [ $C_ERR -eq 1 ]; then
  echo
  echo "REVIEW_ENVIRONMENT_UNAVAILABLE"
  echo "NO_BYTE_DRIFT_PROVEN"
  echo "NO_REVIEW_VERDICT_PRODUCED"
  exit 3
fi

# Class A Checks (Candidate Bytes)
A=0
echo "CLASS A — candidate bytes"
[ "$wh" = "$B" ] && r "review worktree HEAD" "OK" || { r "review worktree HEAD" "CHANGED $wh"; A=1; }
d=$(git -C $W status --porcelain 2>/dev/null | wc -l | tr -d ' '); [ "$d" = "0" ] && r "review worktree clean" "OK" || { r "review worktree clean" "DIRTY ($d)"; A=1; }
while read -r want path; do
  got=$(sha256sum "$W/$path" 2>/dev/null | cut -d' ' -f1)
  [ "$got" = "$want" ] && r "snapshot $(basename $path)" "OK ${got:0:16}…" || { r "snapshot $(basename $path)" "BYTES DIFFER"; A=1; }
done < <(python3 -c "import json;d=json.load(open('$L'));[print(v,k) for k,v in d['pinned_snapshots'].items()]")

# Class B Checks (Promotion Binding)
Bf=0
echo "CLASS B — promotion binding"
h=$(git rev-parse HEAD); [ "$h" = "$B" ] && r "branch HEAD" "OK" || { r "branch HEAD" "MOVED $h"; Bf=1; }
[ "$remote_head" = "$B" ] && r "remote ref ($target_branch)" "OK" || { r "remote ref ($target_branch)" "MOVED $remote_head"; Bf=1; }
reg=$(python3 -c "import json;print(json.load(open('coordination/governance/open_claims_register.json')).get('recorded_head'))")
[ "$reg" = "$B" ] && r "register.recorded_head" "OK" || { r "register.recorded_head" "DIVERGED $reg"; Bf=1; }
if [ "$expiry_status" = "EXPIRED" ]; then
  r "lease not expired" "EXPIRED"
  Bf=1
else
  r "lease not expired" "OK"
fi

echo
if [ $A -eq 1 ]; then
  echo "REVIEW_INVALIDATED — the reviewed bytes changed. Findings do NOT carry over."
  echo "Do NOT restart silently. Capture the new HEAD and open a new lease."; exit 1
fi
if [ $Bf -eq 1 ]; then
  echo "PROMOTION_BINDING_STALE"
  echo "REVIEW_REMAINS_VALID_FOR_PINNED_SHA $B"
  echo "Findings stand (commit objects are immutable). Rebind before promoting."; exit 2
fi
echo "REVIEW BASELINE INTACT — candidate bytes and promotion binding both current"; exit 0
