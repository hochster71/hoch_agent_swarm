# Canonical Control Plane — declaration

- Declared (UTC): 2026-07-06 · Shell decision RESOLVED 2026-07-06
- Status: ADOPTED contract for UI consolidation (supersedes ad-hoc surface creation)
- Source audit: `docs/evidence/ui/ui_audit_consolidation_20260706T143307Z.md`
- Migration plan: `docs/ui/CONTROL_PLANE_P2_MIGRATION.md`

## The one surface (RESOLVED)

**The React SPA (`hoch-swarm-dashboard`, built from `frontend/` → `frontend/dist/`, served by the
nginx container at `http://127.0.0.1:8080/`) is the single canonical control-plane SHELL.**

**`backend/pert_server.py` (`:8765`) is demoted to an API/data backend** — it keeps its `/api/*`
endpoints (`/api/pert/data`, telemetry, pods, revenue, approvals, relay) but its hand-written
inline-HTML pages (`/`, `/ui-v2`) are ported into React tabs and then retired.

The shell is **factory-aware**: one nav switches across **HAS, HASF, HMF, HRF**, each reading the
**single shared status feed** so numbers agree everywhere (kills the 80%-vs-95% divergence).

### Why the React SPA (evidence, not preference)
- 141 components, actively developed (247 source files touched since Jul 1).
- Already wired to real endpoints: `/api/v1/hochster/*`, `/api/v1/promptops/*`,
  `/api/v1/runtime-truth/*`, `/api/approval`, `/api/audit`.
- Deployed as a container (`Dockerfile.frontend` → nginx `:8080`, in `docker-compose.yml`).
- Component-based and testable. The `:8765` inline-HTML-in-Python approach is *how the sprawl
  happened*; making it the shell would repeat the mistake.

## Everything else — disposition

| Surface | Disposition |
|---------|-------------|
| React SPA (`frontend/` → nginx `:8080`) | **CANONICAL SHELL** — add factory-aware tab nav |
| `backend/pert_server.py` (`:8765`) | **API/DATA BACKEND** — keep `/api/*`; port then retire inline HTML |
| `/` PERT Command Center (inline HTML) | PORT to a React "PERT / Critical Path" tab, then retire the route |
| `/ui-v2` | PORT into the shell, then retire route |
| `/ui-moonshot` (PODS Theater V6) | EMBED as a React tab (iframe or port); retain its 42 tests |
| BRAIN Command Deck (`frontend/has_brain_moonshot.html`) | EMBED/port as a "BRAIN" tab; repoint to `:8765` API; retire Tailscale-only serving |
| BRAIN Console (`has_brain_console.html`) | RETIRE if superseded, else fold in |
| standalone `frontend/index.html` (5,964 lines) | AUDIT vs the React entry; retire the duplicate |
| VPS relay dashboard (`infra/hoch-200/vps/dashboard/`) | KEEP as a linked panel (host-local on the VPS) |
| `mockups/visual-control-plane/*` (22) | DONE — archived to `archive/mockups-visual-control-plane/` |
| `data/prompt_registry/dashboard.html` ≡ `docs/dashboard.html` | DONE — deduped (deleted the 3.3 MB copy) |

## The `/docs` exposure note
`pert_server.py` mounts the **entire `docs/` tree** as StaticFiles at `:8765/docs/…` (evidence,
runbooks, business docs). Localhost/Tailscale only, but a wide internal surface — scope this during
P2 (serve only what the shell needs).

## Rule going forward

> New status/telemetry needs are satisfied by adding a **tab/panel to the React shell**, reading the
> **shared status feed** from the `:8765` API backend. Creating a new standalone HTML surface, or
> adding a new inline-HTML page to `pert_server.py`, requires an explicit operator decision and an
> entry in this disposition table.
