# HELM control-surface map — twin/triple FastAPI apps (audit #5b)

**Verify-first finding (Builder/Claude, 2026-07-17).** The Kimi/Grok audit flagged "dual control
surfaces / process drift" between `backend/main.py` and `backend/helm_live_api.py`. On inspection
there are **three** FastAPI apps, on **distinct ports**, owning **distinct route surfaces** — not
two apps serving the same routes. The honest risk is *cognitive/operational* (which app owns what)
plus `main.py`'s monolith size, **not** conflicting duplicate endpoints.

## The three apps
| App | Title | Routes | Port | Served by | Role |
|---|---|---|---|---|---|
| `backend.main:app` | "Hoch Agent Swarm Control API" | **576** | 8000 | `scripts/start_has_runtime.sh` (launchd), `helm_supervisor.py`, CI | Legacy monolith — the full swarm control API (721 KB source). |
| `backend.helm_live_api:app` | "HELM LIVE" | **68** | 8770 | `helm_restart_api.sh`, `helm_autoloop.sh`, docker-compose mirror | HELM executive surface — Council, Overview, PERT-live, Build/Audit theaters, voice, executive-brief. (TLS :8443 in the browser sits in front of :8770.) |
| `backend.pert_server:app` | (PERT) | — | 8765 | the `rc*_verify.sh` scripts | PERT visualization server used by verification runs. |

## Collision analysis (the actual "drift")
Route-path overlap between `main` (576) and `helm_live_api` (68): **exactly one — `/favicon.ico`.**
There is **no meaningful duplicate-endpoint conflict**; the two apps own separate surfaces. So the
audit's "process drift" is real as *operational ambiguity* (two long-lived apps, two ports, unclear
boundary) but is **not** a case of two planes answering the same routes differently.

## Already in motion: the `main`-split-plan
`backend/routers/` shows the monolith is **already being decomposed** into routers (extracted so
far: `app_store.py`, `stripe_billing.py`, `stripe_webhook.py`; headers say *"extracted from
backend/main.py (main-split-plan step)"*). This is the sanctioned direction — incremental extraction,
not a big-bang merge.

## Safe consolidation sequence (no redesign — Grok's constraint)
1. **Declare ownership (this doc).** `main:app` = swarm control API (:8000); `helm_live_api:app` =
   HELM executive/governance surface (:8770→:8443); `pert_server:app` = PERT viz (:8765). Any new
   executive/governance route belongs in `helm_live_api`, not `main`.
2. **Continue the main-split-plan** — keep extracting cohesive router groups from `main.py` into
   `backend/routers/`, one guarded PR each, tests green per extraction. Shrinks the 721 KB monolith
   without moving behavior.
3. **De-dupe the one real collision** — pick a single owner for `/favicon.ico` (cosmetic).
4. **Do NOT merge the apps.** They serve different lifecycles/ports; merging is high-blast-radius
   and unnecessary — the drift is resolved by ownership clarity + continued extraction.

## Status
- **DONE:** surface mapped, collision analysis complete (only `/favicon.ico`), ownership declared,
  split-plan confirmed in progress.
- **PENDING (own guarded passes):** each `main.py` router extraction; favicon owner pick. These are
  incremental and low-risk but out of scope for a tail-of-pass edit — tracked here and in the
  remediation ledger. No behavior changed in this pass (map only).
