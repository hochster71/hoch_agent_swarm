# UI Audit + Consolidation Plan — one control plane

- Captured (UTC): 2026-07-06 14:33
- Author: Claude (analysis), for operator review
- Repo REVISION: `68a4bf8` · committed checkpoint HEAD `fff73b6`
- Trigger: operator observation — "we have so many UIs… consolidate to one main control plane."

---

## 0. Direct answer: is `/ui-moonshot` part of the build?

**Yes — it's a live, tested surface.** `backend/pert_server.py` serves it at `@app.get("/ui-moonshot")` (line 7437), reading `has_live_project_tracker/ui/hoch_pods_liftoff.html` (HOCH PODS Theater V6). It's covered by **42 Playwright E2E tests** and the visual-compliance gate that both passed in today's `rc50_full_cascade_verify.sh` run. So it's not stray — it's arguably the *most*-tested UI. The problem isn't that `/ui-moonshot` exists; it's that it's **one of ~7 live surfaces plus 22 mockups**, with no single canonical control plane.

---

## 1. UI inventory (what exists today)

### A. Live / served surfaces
| # | Surface | Served by | Data | Tests |
|---|---------|-----------|------|-------|
| 1 | `/` — PERT Command Center | pert_server.py :8765 | `/api/pert/data`, telemetry, pods, revenue, approvals, relay | RC32/33/34 + mirror gates |
| 2 | `/ui-v2` — Operator Console V2.1 | pert_server.py :8765 | same backend | ui-v21 spec |
| 3 | `/ui-moonshot` — HOCH PODS Theater V6 | pert_server.py :8765 → `hoch_pods_liftoff.html` | `/api/pert/data` | 42 Playwright + visual compliance |
| 4 | React app "hoch-swarm-dashboard" | `frontend/` (vite build → `dist/`) | cluster/orchestration | vite build gate |
| 5 | BRAIN Command Deck | `frontend/has_brain_moonshot.html` (Tailscale) | `/api/brain/live` (:8000) | session e2e (this session) |
| 6 | BRAIN Console | `frontend/has_brain_console.html` | brain feeds | — |
| 7 | VPS relay dashboard | `infra/hoch-200/vps/dashboard/index.html` | relay :3012 | relay gates |

### B. Non-production (mockups / generated / archive)
- `mockups/visual-control-plane/*.html` — **22 design mockups** (agents, approvals, assets, cyber, evidence, factory, life-*, models, prompts, …). Design reference, not wired to data.
- `data/prompt_registry/dashboard.html` **≡** `docs/dashboard.html` — **identical 3.3 MB file, duplicated** (same md5). ~6.6 MB of repo weight for one generated artifact.
- `frontend/archive/unused_views.html`, `docs/evidence/ui/approved-visual-authority-review.html`, `has_brain_moonshot.backup_*.html` (now gitignored).

**Count: 7 live surfaces + 22 mockups + 4 generated/archive = 33 HTML UIs.** Two different servers (FastAPI :8765, `/api/brain/live` :8000), plus the Tailscale-served BRAIN deck, plus a separate vite React app. That is the sprawl you're feeling.

---

## 2. Root cause — three, all fixable

1. **No designated canonical control plane.** Surfaces 1–7 each grew for a specific demo/RC; none was declared "the one," so each new need spawned a new page.
2. **Multiple sources of truth.** Today's cascade shows it directly: the operator brief printed **80% complete** while the control-plane snapshot says **95%**; BRAIN reports CONVERGED at 75.48 (proxy). Different UIs read different feeds, so numbers disagree. One control plane forces one number.
3. **Generation without garbage-collection.** The AG usage gate in the same run flagged **1316 files changed, 205 new scripts, 78 new tests** against caps of 10/3/2 — the system produces surface area faster than it retires it. The 22 mockups + duplicated 3.3 MB dashboard are the UI symptom.

---

## 3. Recommendation — consolidate onto the :8765 PERT Command Center

Pick **surface #1 (`/` on :8765)** as the single canonical control plane. Why it wins over the others: it already aggregates the most (PERT/CPM, telemetry-truth, pods, revenue readiness, approvals queue, relay/port security), it has the deepest test coverage, and it owns the `/api/*` spine the other surfaces already call. Everything else becomes a **tab/panel inside it or is retired.**

### Target: one control plane, tabbed
```
HOCH Control Plane (:8765/)
├─ Overview        ← status roll-up: goal %, readiness, blockers, approvals (ONE source of truth)
├─ PERT / Critical Path   ← current /  + /ui-v2 content
├─ PODS Theater    ← /ui-moonshot (hoch_pods_liftoff) as an embedded tab, not a separate URL
├─ BRAIN Deck      ← has_brain_moonshot.html folded in (point it at :8765, retire the Tailscale-only variant)
├─ Relay / HOCH-200 ← infra VPS dashboard as a panel
└─ Evidence        ← /view-doc + /docs
```

### Disposition table
| Surface | Action |
|---------|--------|
| `/` PERT Command Center | **KEEP — canonical.** Add top-level tab nav. |
| `/ui-v2` | **MERGE** into `/` as a tab, then retire the route. |
| `/ui-moonshot` (PODS Theater) | **KEEP as a tab** inside `/`; keep its 42 tests. Stop treating as standalone. |
| BRAIN Command Deck (`has_brain_moonshot.html`) | **MERGE** as a tab; repoint to :8765; retire Tailscale-only serving. |
| BRAIN Console (`has_brain_console.html`) | **RETIRE** if superseded by the deck; else fold in. |
| React "hoch-swarm-dashboard" | **DECIDE:** either it *is* the shell that hosts the tabs, or it's retired in favor of the server-rendered pages. Do not keep both silently. |
| VPS relay dashboard | **KEEP** as a linked panel (it's host-local on the VPS). |
| `mockups/visual-control-plane/*` (22) | **ARCHIVE** to a design-only folder, exclude from build/serving. |
| `data/prompt_registry/dashboard.html` + `docs/dashboard.html` (dup 3.3 MB) | **DEDUPE** — keep one, delete the copy (~3.3 MB reclaimed). |
| `frontend/archive/*`, backups | Already inert / gitignored. Leave. |

### The one hard decision for the operator (blocks the rest)
**Server-rendered (:8765 FastAPI HTML) vs. the React SPA — which is the shell?** These are two parallel front-end stacks. Consolidation can't finish until one is chosen. Recommendation: **server-rendered :8765 as the shell** (it already holds the data spine and tests), and retire or repurpose the standalone React build — unless there's a reason the SPA must stay, in which case flip it and make :8765 an API-only backend.

---

## 4. Phased plan (additive, gated — no rip-out without approval)

- **P1 (agent-safe, no UX change):** Archive the 22 mockups out of any served path; dedupe the 3.3 MB dashboard; write a `docs/ui/CANONICAL_CONTROL_PLANE.md` declaring `/` on :8765 as the one surface. Reclaims weight, sets the contract.
- **P2 (needs the §3 shell decision):** Add tab nav to `/`; embed PODS Theater and BRAIN Deck as tabs; make the Overview tab read a **single** status feed so 80% vs 95% can't happen again.
- **P3:** Retire `/ui-v2` and the Tailscale-only BRAIN serving once their content lives in the tabs. Keep all existing tests; re-point them at the tabs.
- **P4:** One redirect map — every old URL 302s to the canonical tab, so nothing 404s and muscle memory still works.

---

## 5. Cross-reference — today's cascade findings (context)
- `rc50_full_cascade_verify.sh`: **near-green**; Playwright 42/42, RC26 13/13, RC28 16/16, RC33 2/2, doctrine DB healthy (122 rules), port 3012 closed, no fake-status.
- **One gate FAIL** — Secure Build Guardrails: `access_token = "access-sandbox-mock"` in `backend/main.py` (mock, not a real secret) + two files whose *names* contain "secret" (`epic-fury-secret-rotation.md`, `test_no_literal_secrets.py`). All three are **false positives**; the guardrail needs an allowlist, not a code change. This blocks release-tag validation (`v0.1.8: FAIL`) until resolved.
- Percent-complete disagreement (80% brief vs 95% snapshot) is the same one-source-of-truth issue this consolidation fixes.

---

## Sources (repo)
- `backend/pert_server.py` (routes: `/`, `/ui-v2`, `/ui-moonshot`, `/view-doc`; :8765)
- `has_live_project_tracker/ui/hoch_pods_liftoff.html` (PODS Theater V6)
- `frontend/index.html`, `frontend/package.json`, `frontend/src/` (React "hoch-swarm-dashboard")
- `frontend/has_brain_moonshot.html`, `has_brain_console.html`
- `mockups/visual-control-plane/*` (22), `data/prompt_registry/dashboard.html` ≡ `docs/dashboard.html`
- `rc50_full_cascade_verify.sh` run output 2026-07-06 (guardrail FAIL, 42 Playwright PASS)
