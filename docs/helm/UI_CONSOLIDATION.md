# HELM UI Consolidation — keep / merge / retire

**Pass 1 (2026-07-17, Builder).** HELM served **19 HTML routes** with real overlap and one route
bug. This pass introduces a single front door (the **Hub**) and records the keep/merge/retire
plan. No distinct page was deleted; consolidation is additive + documented (governed change).

## Front door
- **`/` and `/hub` → `hub.html`** (new). The single entry: 5 keeper cockpits with live GOAL% +
  lane status, plus grouped links to specialized/legacy views. Everything is reachable from here.

## KEEP — the 5 primary cockpits
| Route | Page | Purpose |
|---|---|---|
| `/council` | council.html | Converse with the whole council (Orchestrator/Builder/Auditor/Local); it routes, reasons, builds. |
| `/command` | *(see bug)* | Executive Command Center — every subsystem's runtime truth in one wall. |
| `/pert-live` | pert_live.html | Live PERT→GOAL board (node status + %). |
| `/build` | build_theater.html | Build Theater — live reasoning stream as the swarm builds. |
| `/audit` | audit_theater.html | Audit Theater — autonomous audit swarm driving audits to GREEN. |

## SPECIALIZED / REFERENCE — kept, grouped under "More views" in the Hub
`/architecture` (`/arch`), `/roadmap`, `/voice`, `/founder` (iPhone gate), `/jspace`,
`/executive`, `/mission`, `/theater` (pods/swarm-launch viz), `/pert` (85″ wall), `/nist`.
These are distinct, still-useful views — not duplicates. Left in place; surfaced via the Hub.

## PASS 2 (2026-07-17) — RESOLVED
- **`/command` double-registration bug FIXED.** The shadowed second handler moved to
  `/command-wall` (command.html now reachable); `/command` is a single registration serving the
  15-panel executive-brief Command Center.
- **Dead pages retired via 307 redirect** (non-destructive, reversible; bookmarks still resolve):
  `/console → /command`, `/control_plane → /council`, `/brain → /jspace`, `/helm → /hub`.
  The old cinematic brain view is preserved at `/brain-classic`.

## FINDINGS (original — now addressed in Pass 2 above)
1. **BUG — `/command` is registered twice.** Two `@app.get("/command")` handlers exist
   (`command_center.html` at the first definition wins; `command.html` at the second is
   **shadowed / unreachable**). Decide the canonical Command Center page and remove the other
   registration. Until then, `/command` = `command_center.html`.
2. **Overlapping "control plane" views** — `/console`, `/control_plane`, `/brain`, `/jspace`,
   `/helm` predate the Council + Command Center and overlap heavily. Candidate to merge/retire
   after confirming nothing links to them.
3. **`command_center.html` vs `command.html`** — two Command Center designs; pick one.

## Recommendation
Ship the Hub now (done). Do the retire/merge of items in FINDINGS as a follow-up UI pass with
per-page confirmation (safe-autonomy: redirect or retire only after verifying no live dependency).
