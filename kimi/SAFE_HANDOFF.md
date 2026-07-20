# Kimi safe handoff (fail-closed)

Use this when you want **Kimi 3.0 throughput** without feeding the monorepo or secrets to Moonshot.

## Command

```bash
# From monorepo root
scripts/kimi/make_safe_handoff.sh <path> [paths...] \
  --label short-name \
  --task "What Kimi should do (abstract, no secrets)"

# Dry-run first (recommended)
scripts/kimi/make_safe_handoff.sh <path> --dry-run
```

## What it does

1. **Deny-list** — refuses crown jewels (`.env`, `coordination/`, `backend/helm_runtime/`, EDRs, ledgers, etc.)  
   Config: `scripts/kimi/deny_paths.txt`
2. **Secret redaction** — keys, tokens, private key blocks, DB URLs → `REDACTED_*`
3. **Residual scan** — if secrets still remain after redaction, **pack is deleted** (fail-closed)
4. **Soft token rename** — HELM/brand strings → generic names  
   Config: `scripts/kimi/token_map.txt` (`--no-rename` to skip)
5. **Drops pack** into  
   `~/Documents/kimi/workspace/_inbox_from_helm/pack_<ts>_<label>/`  
   plus a `.tgz` next to it
6. **Prepares outbox**  
   `~/Documents/kimi/workspace/_outbox_to_helm/pack_.../`

## Pack contents

| File | Purpose |
|------|---------|
| `TASK.md` | Kimi instructions (template + your task) |
| `ALLOWED.md` | Hard boundaries |
| `source/` | Redacted files only |
| `MANIFEST.json` | Inventory |
| `SCAN_REPORT.json` | Deny / redact / residual evidence |

## Workflow

```text
HELM (you/Claude)  →  make_safe_handoff  →  Kimi inbox pack
Kimi works only in Documents/kimi/workspace
Kimi writes outbox  →  you review  →  promote into monorepo if good
```

## Never

- Point Kimi at `hoch_agent_swarm` root  
- Pack secrets, mission runtime, settlement, customer data  
- Reconstruct `REDACTED_*` values  

## Approval policy (founder rule)

The packager is a **trust-boundary tool**. Edits under `scripts/kimi/**` (and the adversarial redaction tests) require **per-action founder approval** — not always-approve.

| Layer | Setting |
|-------|---------|
| Grok global | `~/.grok/config.toml` → `[ui] permission_mode = "default"` |
| Project | `.grok/config.toml` → `ask` on `Edit(scripts/kimi/**)` and related shell |
| Restart | New Grok session required for permission rules to load |

Do not re-enable always-approve while authoring or changing the handoff redactor.

**Hard lock (operator machine):** `~/.grok/requirements.toml` has
`disable_bypass_permissions_mode = true` so `/always-approve` cannot silently
disable non-shell `ask` rules (including `Edit(scripts/kimi/**)`).
Restart Grok after changing requirements.toml.

## Related

- Isolation: `~/Documents/kimi/policy/ISOLATION.md`
- Verify: `scripts/kimi/verify_isolation.sh`
- Enforce: `scripts/kimi/enforce_isolation.sh`
