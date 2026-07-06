# Control Plane P2 — migration plan (React shell + :8765 API backend)

- Captured (UTC): 2026-07-06
- Decision source: `docs/ui/CANONICAL_CONTROL_PLANE.md` (React SPA `:8080` = shell; `:8765` = API)
- Scope: HAS · HASF · HMF · HRF under one factory-aware shell, one status feed.
- Principle: additive and reversible first; retire only after the replacement is proven. No fake-green.

## Target architecture
```
React shell (:8080, nginx)                 :8765 pert_server  →  API/data backend
├─ Factory switcher: HAS│HASF│HMF│HRF        /api/v1/control-plane/status   (NEW, single source of truth)
├─ Overview     ← one status feed            /api/pert/data, /api/v1/hochster/*, /promptops/*,
├─ PERT/Critical Path ← port of :8765 "/"    /runtime-truth/*, /approval, /audit  (existing)
├─ PODS Theater ← embed /ui-moonshot
├─ BRAIN Deck   ← port of has_brain_moonshot (reads /api/brain/live)
├─ Approvals    ← /api/approval
└─ Evidence     ← scoped docs, not the whole tree
```

## Slice order (each independently shippable, gated)

**S1 — Single status feed (highest leverage, do first).**
Add `GET /api/v1/control-plane/status` to `:8765` returning ONE authoritative object:
`{goal_percent, readiness, blockers[], critical_path, tests, approvals[], per_factory{HAS,HASF,HMF,HRF}}`.
It reads the existing sources and reconciles them so 80%-vs-95% cannot recur. Additive (new endpoint,
nothing removed). The React Overview tab and any legacy page both consume it.
*First concrete step; agent-safe; show-before on the pert_server edit.*

**S2 — Factory-aware Overview tab in the React shell.**
New `OverviewDashboard.tsx` + a `FactorySwitcher` reading `/api/v1/control-plane/status`. No retirement yet.

**S3 — Port PERT/Critical Path.** Recreate the `:8765` "/" content as a React tab against `/api/pert/data`. Keep the old route live until the tab passes the equivalent of its RC32/33/34 checks.

**S4 — Embed PODS Theater + BRAIN Deck as tabs.** iframe `/ui-moonshot` (keep its 42 Playwright tests pointed at it) and port/repoint `has_brain_moonshot.html` to the `:8765` `/api/brain/live` API; retire the Tailscale-only serving.

**S5 — Retire, with redirects.** Once S3/S4 tabs are proven: retire `/`, `/ui-v2`, standalone `frontend/index.html`, `has_brain_console.html`. Add a redirect map so every old URL 302s to its new tab (nothing 404s).

**S6 — Scope the `/docs` static mount** to only what the shell needs (stop serving the whole `docs/` tree).

## Redirect map (S5)
| Old | New |
|-----|-----|
| `:8765/` | `:8080/#/pert` |
| `:8765/ui-v2` | `:8080/#/pert` |
| `:8765/ui-moonshot` | `:8080/#/pods` |
| Tailscale `has_brain_moonshot.html` | `:8080/#/brain` |

## Test continuity (no coverage loss)
- The 42 Playwright E2E + visual-compliance gate stay pointed at PODS Theater through the embed.
- RC32/33/34 assert `:8765` API health — unaffected (backend stays).
- Add a shell smoke test per new tab before retiring its legacy source.

## Risks / guards
- **Don't retire before parity.** Each legacy surface stays live until its replacement passes an equivalent check.
- **Two servers during migration** (`:8080` shell + `:8765` API) is expected and fine; the point is one *shell*, not one process.
- **`frontend/index.html` (5,964 lines) vs the React entry** — confirm which is the real vite entry before touching (they may be the same file; the build wrote `dist/index.html` 512 KB).
- **Daemon/git contention** — every commit in this migration uses the show-before + stale-lock guard already established this session.

## First action on your go
Implement **S1** (the single status feed) — one additive endpoint on `:8765`, show-before diff, then wire the React Overview to it. It fixes the most visible symptom (divergent numbers) and unblocks S2 without retiring anything.
