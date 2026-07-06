# Canonical Control Plane — declaration

- Declared (UTC): 2026-07-06
- Status: ADOPTED contract for UI consolidation (supersedes ad-hoc surface creation)
- Source audit: `docs/evidence/ui/ui_audit_consolidation_20260706T143307Z.md`

## The one surface

**`http://127.0.0.1:8765/` (the PERT Command Center, served by `backend/pert_server.py`) is the single canonical control plane.**

All operational status — goal %, readiness, PERT critical path, pods, revenue readiness,
approvals queue, relay/port security, BRAIN state, evidence — is presented here, reading a
**single source of truth**. No new standalone UI surface may be created; new views are added as
**tabs/panels within this control plane.**

## Why this surface

It already owns the `/api/*` data spine the other surfaces call, aggregates the most domains, and
carries the deepest test coverage (RC32/33/34 + 42 Playwright E2E + visual-compliance gate).

## Everything else — disposition

| Surface | Disposition |
|---------|-------------|
| `/` PERT Command Center (:8765) | CANONICAL — add tab nav |
| `/ui-v2` | MERGE into `/` as a tab, then retire route |
| `/ui-moonshot` (PODS Theater V6) | KEEP as an embedded tab; retain its 42 tests |
| BRAIN Command Deck (`frontend/has_brain_moonshot.html`) | MERGE as a tab; repoint to :8765; retire Tailscale-only serving |
| BRAIN Console (`has_brain_console.html`) | RETIRE if superseded, else fold in |
| React "hoch-swarm-dashboard" (`frontend/` → `dist/`) | DECIDE (see below); do not run two front-end stacks silently |
| VPS relay dashboard (`infra/hoch-200/vps/dashboard/`) | KEEP as linked panel (host-local on VPS) |
| `mockups/visual-control-plane/*` (22) | ARCHIVE to design-only, exclude from any served path |
| `data/prompt_registry/dashboard.html` ≡ `docs/dashboard.html` | DEDUPE (identical 3.3 MB); keep one |

## Open decision that blocks completion

**Server-rendered `:8765` FastAPI HTML vs. the React SPA — which is the shell?** These are two
parallel front-end stacks. Recommendation: `:8765` server-rendered as the shell (it holds the data
spine and tests); repurpose or retire the standalone React build. Flip only if the SPA must remain,
in which case `:8765` becomes API-only.

## Rule going forward

> New status/telemetry needs are satisfied by adding a tab or panel to the canonical control plane,
> reading the shared status feed. Creating a new standalone HTML surface requires an explicit
> operator decision and an entry in this file's disposition table.
