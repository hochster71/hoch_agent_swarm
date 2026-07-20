# Kimi-safe task

**Pack id:** `{{PACK_ID}}`  
**Created:** `{{CREATED_AT}}`  
**Source root (monorepo-relative or path label):** `{{SOURCE_LABEL}}`  
**Mode:** sanitised handoff — you do **not** have the HELM monorepo

---

## Your workspace

You may only read/write under:

```text
~/Documents/kimi/workspace
```

This pack landed in:

```text
_inbox_from_helm/{{PACK_ID}}/
```

Deliver results to:

```text
_outbox_to_helm/{{PACK_ID}}/
```

---

## Task (founder / HELM agent)

{{TASK_BODY}}

---

## Hard rules

1. Work **only** from the files under `source/` in this pack plus your own workspace.
2. Do **not** open, search, or read `/Users/michaelhoch/hoch_agent_swarm` or any monorepo path.
3. Do **not** invent secrets, keys, tokens, or claim live production state.
4. If a file looks redacted (`REDACTED_*`), leave it redacted — do not reconstruct secrets.
5. Prefer diffs / patches / new files in `_outbox_to_helm/{{PACK_ID}}/` over rewriting the whole tree.
6. If the pack is insufficient, write `_outbox_to_helm/{{PACK_ID}}/NEED_MORE_CONTEXT.md` listing **abstract** needs (no demand for monorepo access).

---

## Expected deliverables

- `SUMMARY.md` — what you changed and why  
- `CHANGES/` — proposed files or unified diffs  
- `RISKS.md` — residual risk, assumptions, unknowns  
- Optional: tests you would run (as commands / checklists, not live monorepo execution)

---

## Scan status

See `SCAN_REPORT.json` and `MANIFEST.json` in this pack. Pack was fail-closed: secrets either redacted or the pack was refused.
