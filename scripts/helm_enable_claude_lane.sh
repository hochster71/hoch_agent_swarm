#!/usr/bin/env bash
# HELM — enable the Claude (Opus) frontier lane on the Council.
#
# This is a FOUNDER GATE: running this script is your explicit approval of a frontier
# escalation. It grants CLI_CLAUDE in the guarded gateway policy and opts the Builder lane
# into Claude. Claude runs via your existing `claude` CLI auth (Max subscription or your
# login) — NO API key is handled or stored here. All Claude calls still go through HELM's
# guarded gateway (cost-capped at the policy monthly cap, ledgered, local_only environment).
set -uo pipefail
REPO="/Users/michaelhoch/hoch_agent_swarm"
POLICY="$REPO/coordination/council/gateway_policy.json"
ENVFILE="$HOME/.helm/helm.env"
LANES="${1:-builder}"   # which lane(s) run Claude; default: builder. e.g. bash ... "builder,auditor"

echo "▸ Enable Claude (Opus) frontier lane — founder approval by running this"
echo

# 1) claude CLI must be present + authenticated (uses YOUR Claude auth; no key here).
if ! command -v claude >/dev/null 2>&1; then
  echo "  ✗ 'claude' CLI not found on PATH. Install Claude Code and sign in first, then re-run."
  echo "    (Claude Code is what runs Opus as you — that's the no-API-key path.)"
  exit 1
fi
echo "  ✓ claude CLI found: $(command -v claude)"

# 2) Grant CLI_CLAUDE in the guarded gateway policy (idempotent, backed up first).
[ -f "$POLICY" ] || { echo "  ✗ policy not found: $POLICY"; exit 1; }
cp "$POLICY" "$POLICY.bak.$(date -u +%Y%m%dT%H%M%SZ)"
python3 - "$POLICY" <<'PY'
import json, sys
p = sys.argv[1]
d = json.load(open(p))
dt = d.setdefault("authorized_dispatch_types", [])
ad = d.setdefault("authorized_adapters", [])
changed = False
if "CLI_CLAUDE" not in dt: dt.append("CLI_CLAUDE"); changed = True
if "claude" not in ad: ad.append("claude"); changed = True
# keep frontier escalation-only + the money cap intact (do NOT loosen those)
json.dump(d, open(p, "w"), indent=2)
print("  ✓ policy updated: CLI_CLAUDE + claude authorized" if changed
      else "  ✓ policy already grants CLI_CLAUDE (no change)")
print(f"    authorized_dispatch_types = {d['authorized_dispatch_types']}")
print(f"    monthly_cap_usd = {d.get('monthly_cap_usd')}  (hard ceiling, unchanged)")
PY

# 3) Opt the chosen lane(s) into Claude (persisted so the server picks it up on restart).
mkdir -p "$(dirname "$ENVFILE")"; touch "$ENVFILE"; chmod 600 "$ENVFILE"
grep -v '^HELM_COUNCIL_CLAUDE_LANES=' "$ENVFILE" > "$ENVFILE.tmp" 2>/dev/null || true
mv "$ENVFILE.tmp" "$ENVFILE"; chmod 600 "$ENVFILE"
echo "HELM_COUNCIL_CLAUDE_LANES=$LANES" >> "$ENVFILE"
echo "  ✓ lane(s) → Claude: $LANES  (persisted in ~/.helm/helm.env)"

echo
echo "✓ Claude (Opus) lane enabled — guarded, cost-capped, ledgered."
echo "  Next: restart so the server loads it:"
echo "    cd ~/hoch_agent_swarm && bash scripts/helm_restart_api.sh"
echo "  Then open /council — the '$LANES' lane now answers as Claude (Opus)."
echo "  Cost: Claude runs on your existing auth; the gateway caps all frontier spend at the"
echo "        policy monthly_cap_usd. Local lanes stay \$0. To revert: remove CLI_CLAUDE from"
echo "        $POLICY (a .bak was saved) and delete the HELM_COUNCIL_CLAUDE_LANES line."
