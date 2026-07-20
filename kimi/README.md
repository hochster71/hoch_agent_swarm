# Kimi fence (NOT a Kimi Desktop workspace)

**Do not open this monorepo — or this folder — as a Kimi Desktop project root.**

Kimi Desktop’s only project workspace is:

```text
~/Documents/kimi/workspace
```

Policy: `~/Documents/kimi/policy/ISOLATION.md`  
Verify: `~/Documents/kimi/policy/verify_isolation.sh`  
(also mirrored at `scripts/kimi/verify_isolation.sh`)

## Why this directory exists

This is a **monorepo fence / pointer** so humans and other agents do not re-invite Kimi into HELM source. It is not a writable Kimi sandbox inside the monorepo.

## Product code named “kimi-*”

Frontend `kimi-*` CSS and the “Kimi-style Comic Swarm” demo are **product design tokens**, not Kimi Desktop agent storage. They stay under `frontend/` and `scripts/qa/`.

## Handoffs (use the packager — do not raw-copy)

| Direction | Path |
|-----------|------|
| HELM → Kimi | `scripts/kimi/make_safe_handoff.sh <paths> --task "..."` → `_inbox_from_helm/` |
| Kimi → HELM | Kimi writes `_outbox_to_helm/`; founder promotes after review |

Full guide: [`SAFE_HANDOFF.md`](./SAFE_HANDOFF.md)

Never symlink monorepo secrets or `coordination/` into the Kimi tree.
