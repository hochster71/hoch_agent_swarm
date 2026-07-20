#!/usr/bin/env bash
# actor_f2_collect.sh — ACTOR-F2 host execution context inventory.
#
# EVIDENCE COLLECTION, NOT AUDIT. Records only directly observed values.
# Never infers. Marks every unobservable field UNKNOWN.
#
# CRITICAL PROPERTY
# -----------------
# A collector run in ONE context observes ONLY that context. It cannot report on the
# others. This script must therefore be executed SEPARATELY INSIDE each execution
# context — Michael's interactive shell, the Claude context, the Gemini/Antigravity
# context, the Grok CLI context, and any other actor able to write to the repository.
# Running it once and treating the output as a survey of the machine would be exactly
# the inference this exercise exists to avoid.
#
# Usage, run INSIDE each context:
#     bash scripts/actor_f2_collect.sh <context-label>
#
# e.g.  bash scripts/actor_f2_collect.sh michael-interactive-shell
#       bash scripts/actor_f2_collect.sh gemini-antigravity
#       bash scripts/actor_f2_collect.sh grok-cli
#
# Appends one JSON record per run to coordination/governance/actor_f2_observations.jsonl
#
# SAFE: read-only. Reads no key MATERIAL — only whether a signing key is CONFIGURED.
# Never prints secrets, key contents, or token values.
set -uo pipefail

LABEL="${1:-UNLABELED}"
[ "$LABEL" = "UNLABELED" ] && {
  echo "FAIL: supply a context label. An unlabelled observation cannot be attributed." >&2
  echo "usage: bash $0 <context-label>" >&2; exit 2; }

REPO=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
OUT="${REPO:-.}/coordination/governance/actor_f2_observations.jsonl"

j() { printf '%s' "$1" | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read()))'; }
val() { local v; v=$("$@" 2>/dev/null); [ -n "$v" ] && printf '%s' "$v" || printf 'UNOBSERVED'; }

# --- process lineage: self and parent, by name where available ---------------
PPID_=$(ps -o ppid= -p $$ 2>/dev/null | tr -d ' ')
PARENT=$(ps -o comm= -p "${PPID_:-0}" 2>/dev/null | sed 's/^-//' || echo UNOBSERVED)
GPPID=$(ps -o ppid= -p "${PPID_:-0}" 2>/dev/null | tr -d ' ')
GPARENT=$(ps -o comm= -p "${GPPID:-0}" 2>/dev/null | sed 's/^-//' || echo UNOBSERVED)

# --- git identity as THIS context resolves it --------------------------------
G_NAME=$(val git config user.name)
G_EMAIL=$(val git config user.email)
G_SIGNKEY=$(git config user.signingkey >/dev/null 2>&1 && echo "CONFIGURED" || echo "UNSET")
G_GPGSIGN=$(val git config commit.gpgsign)
G_FORMAT=$(val git config gpg.format)

# --- selected env vars: PRESENCE ONLY, never values --------------------------
ENVP=""
for v in CLAUDE_CODE_SESSION HELM_SESSION_ID TERM_PROGRAM SSH_CONNECTION \
         GITHUB_ACTIONS CI VSCODE_PID CURSOR_TRACE_ID GEMINI_API_KEY \
         GROK_API_KEY ANTHROPIC_API_KEY GITHUB_TOKEN GH_TOKEN; do
  eval "x=\${$v:-}"
  [ -n "$x" ] && ENVP="${ENVP:+$ENVP,}\"$v\":\"PRESENT\""
done

TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Build the record as compact SINGLE-LINE JSON.
#
# BUG FIXED 2026-07-20: this previously used a multi-line heredoc while the file is
# advertised as .jsonl (one object per line). Nothing round-tripped — the classifier
# could not parse a single record. A collector whose output its own consumer cannot
# read is not a collector. Python does the serialization so quoting is correct by
# construction rather than by careful shell escaping.
python3 - "$OUT" "$LABEL" "$TS" "$(val id -un)" "$(val id -u)" "$(val id -g)" \
  "$(val id -Gn)" "$(val hostname)" "$(val uname -s)" "$(val pwd)" "${REPO:-UNOBSERVED}" \
  "$$" "${PARENT:-UNOBSERVED}" "${GPARENT:-UNOBSERVED}" "$G_NAME" "$G_EMAIL" \
  "$G_SIGNKEY" "$G_GPGSIGN" "$G_FORMAT" "$ENVP" <<'PYEOF'
import json, sys
(out, label, ts, user, uid, gid, groups, host, uname, pwd, repo, pid,
 parent, gparent, gname, gemail, signkey, gpgsign, gformat, envp) = sys.argv[1:21]
env = {}
for pair in [x for x in envp.split(",") if x]:
    k, _, v = pair.partition(":")
    env[k.strip('"')] = v.strip('"')
rec = {
  "artifact": "ACTOR-F2", "context_label": label, "collected_at": ts,
  "observed": {
    "os_user": user, "uid": uid, "gid": gid, "groups": groups, "hostname": host,
    "uname": uname, "pwd": pwd, "repo_toplevel": repo, "shell_pid": pid,
    "parent_process": parent, "grandparent_process": gparent,
    "git_user_name": gname, "git_user_email": gemail, "git_signingkey": signkey,
    "git_commit_gpgsign": gpgsign, "git_gpg_format": gformat, "env_present": env,
  },
  "unknown": [
    "key custody — whether any signing key material is protected from other actors",
    "Secure Enclave usage", "Keychain ACLs",
    "whether this OS user is shared with other execution contexts (determined by COMPARING records, not by any single record)",
  ],
  "inference": "NONE",
  "collector_scope": "This record describes ONLY the context that executed it. It is not evidence about any other actor.",
}
with open(out, "a") as f:
    f.write(json.dumps(rec) + "\n")
PYEOF

echo "recorded: $LABEL"
echo "  os_user  $(val id -un)   uid $(val id -u)   host $(val hostname)"
echo "  git      $G_NAME <$G_EMAIL>   signingkey=$G_SIGNKEY"
echo "  parent   ${PARENT:-UNOBSERVED} <- ${GPARENT:-UNOBSERVED}"
echo "  -> $OUT"
echo
echo "ACTOR-F2 is INCOMPLETE until this has been run inside EVERY execution context."
