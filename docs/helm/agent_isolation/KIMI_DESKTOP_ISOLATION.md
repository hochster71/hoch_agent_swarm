# Kimi Desktop ↔ HELM monorepo isolation

**Status:** ACTIVE (soft isolation)  
**Date:** 2026-07-20  
**Canonical policy:** `~/Documents/kimi/policy/ISOLATION.md`

## Problem found (audit)

1. Kimi Desktop had **registered workspace** = `/Users/michaelhoch/hoch_agent_swarm` (full monorepo).
2. Historical daimon sessions (`wd_hoch_agent_swarm_*`) used `workspacePath` / `workDir` = monorepo root — full filesystem tool access.
3. Active healthy work was already under `~/Documents/kimi/workspace/` (`hjos_sim`, `helm_kimi_brain`) — correct pattern, wrong registry.
4. Monorepo root held loose agent-adjacent droppings (`task.md` Kimi-style mission; `all_model_files.txt` path dump including `kimi-desktop` Application Support paths).

## Immediate actions taken

| Action | Result |
|--------|--------|
| Re-point `created-workspaces.json` | Only `~/Documents/kimi/workspace` |
| Backup pre-change registry | `…/created-workspaces.json.bak.<timestamp>` + `_quarantine/kimi_isolation_*/` |
| Move `task.md` | `~/Documents/kimi/workspace/_from_monorepo/task.md` (+ quarantine copy); removed from monorepo root |
| Move `all_model_files.txt` | `_quarantine/kimi_isolation_*/` (was already gitignored) |
| Policy + verify script | `~/Documents/kimi/policy/` |
| Monorepo fence | `kimi/README.md` |

## Left in monorepo on purpose

- Product UI: `kimi-*` theme / comic-swarm (design namespace, not Desktop agent data)
- QA contract: `scripts/qa/test-kimi-style-comic-swarm-contract.ts`
- HELM evidence *about* Kimi audits: `docs/evidence/audit/KIMI_*`, remediation ledgers, council mentions

## Approach options (for founder)

### A. Soft isolation (current — default)

- Workspace root = `Documents/kimi/workspace` only  
- Handoff via `_inbox_from_helm` / `_outbox_to_helm`  
- Periodic `verify_isolation.sh`  
- **Weakness:** any “Open Folder → monorepo” re-breaches

### B. Soft + social / process

- Role overlay for Kimi: mechanical audits only inside Kimi tree  
- Council bus never stages monorepo paths into Kimi  
- AG IDE / Claude refuse to ask Kimi to open monorepo

### C. Hard isolation (founder gate)

Pick one if soft is not enough:

1. **Dedicated macOS user** for Kimi with ACL/home limited to `Documents/kimi`  
2. **sandbox-exec / Seatbelt** profile denying `hoch_agent_swarm`  
3. **VM or container** with only the Kimi workspace volume mounted  
4. Disable **Computer Use** plugin for Kimi when working near HELM hosts  

Hard options change host security posture — require explicit founder approval.

## Verify

```bash
scripts/kimi/verify_isolation.sh
# or
~/Documents/kimi/policy/verify_isolation.sh
```

## Restore registry (if needed)

```bash
# list backups
ls -la ~/Library/Application\ Support/kimi-desktop/kimi-agent/created-workspaces.json.bak.*
# restore a backup only if intentional
# cp <backup> ~/Library/Application\ Support/kimi-desktop/kimi-agent/created-workspaces.json
```

## Agent approval policy (2026-07-20)

Authoring or changing `scripts/kimi/**` (the packager that decides what may leave the monorepo) requires **per-action founder approval**:

| Layer | Setting |
|-------|---------|
| Grok global | `~/.grok/config.toml` → `permission_mode = "default"` (not `always-approve`) |
| First prompt | `default_selected_permission = "allow_once"` |
| Project | `.grok/config.toml` → `ask` on `Edit(scripts/kimi/**)` and related shell |

Rationale: always-approve while building the trust-boundary redactor is how gaps ship as asserted green. Permission rules load at **session start** — restart Grok for this to take effect.

Note: under always-approve, non-shell `ask` rules do not prompt. Keep always-approve off while working the packager.
