# Chrome window audit + integration plan

**Captured:** 2026-07-13T23:55Z–23:58Z  
**Machine:** local HAS/HELM stack + Tailscale relay surfaces  
**Purpose:** inventory every open Chrome tab, diagnose fragmentation, and prescribe fix/integration steps.

---

## 1. Open Chrome windows (observed)

Single Chrome window, **7 tabs**:

| # | Tab title | URL | Role |
|---|-----------|-----|------|
| 1 | HELM · CONTROL — LIVE | `https://hoch-relay-001.tail826763.ts.net:3012/control` | Relay mission control wall |
| 2 | HAS → GOAL · Board | `https://hoch-relay-001.tail826763.ts.net:3012/board` | Task / goal board |
| 3 | HELM · COUNCIL — Live Coordination Storyboard | `https://hoch-relay-001.tail826763.ts.net:3012/coordination` | Council storyboard |
| 4 | HELM · Factory-Verse | `https://hoch-relay-001.tail826763.ts.net:3012/factoryverse` | 3D factory atrium |
| 5 | HELM · GAP ANALYSIS | `https://hoch-relay-001.tail826763.ts.net:3012/static/helm-gap-analysis.html` | Gap analysis static wall |
| 6 | HELM · PERT · LIVE | `http://127.0.0.1:8770/pert` | **Local** runtime-truth PERT wall |
| 7 | HOCH-200 Relay Dashboard | `https://hoch-relay-001.tail826763.ts.net:3012/` | Relay home / night-watch entry |

**Not open but relevant on this host:** Epic Fury product UI on `:3003` (Next.js).

---

## 2. Process / port map (local)

| Port | Listener | Role | Health at audit |
|------|----------|------|-----------------|
| **3012** | Vite (`frontend`, host 0.0.0.0) | Local SPA + API proxy | HTTP 200 |
| **8000** | `backend.main` (mostly 127.0.0.1) | Primary HAS/HELM API | `/docs` 200; council LOCKED/NO |
| **8770** | `backend.helm_live_api` | HELM LIVE + `/pert` + `/api/helm/live` | Live feed OK; 4 SOAK leases ACTIVE |
| **8765** | `backend.pert_server` | Legacy / parallel PERT command center | `/api/pert/data` 200 |
| **3003** | Epic Fury Next | Champion product | 200 |
| **11434** | Ollama | Local model | LISTEN |
| Tailscale `:3012` | **Relay API** (`infra/hoch-200/vps/relay-api`) | Remote control/board/factoryverse | 200 from tailnet |

**Critical split:** Tabs 1–5/7 hit the **relay** (`hoch-relay-001`). Tab 6 hits **local** `:8770`. Local Vite also owns `:3012` on the Mac — same port number, **different authority** (LAN/local vs tailnet service).

---

## 3. Per-tab audit

### T1 `/control` (relay)

| Check | Result |
|-------|--------|
| Purpose | Live control / night-watch style operator wall |
| Served by | Relay static + `/api/*` state files |
| Risk | May show **synced/stale** JSON unless push path is healthy |
| Local SPA path | Same path on Vite returns **generic dashboard shell**, not the relay wall |

### T2 `/board`

| Check | Result |
|-------|--------|
| Purpose | Goal / task board |
| Served by | Relay |
| Local equivalent | Partial (mission-control views in SPA) — **not the same page** |

### T3 `/coordination`

| Check | Result |
|-------|--------|
| Purpose | Council coordination storyboard |
| Served by | Relay |
| Local truth | Council state on **:8000** (`promotion=LOCKED`, `safe_to_execute=NO`) — may **not** match storyboard animation |

### T4 `/factoryverse`

| Check | Result |
|-------|--------|
| Purpose | 3D factory atrium |
| API | Relay `/api/factoryverse` → `helm_factoryverse.json` |
| Local Vite | **`/api/factoryverse` → 404** (proxied to :8000, route missing) |
| Integration gap | **HIGH** — visual wall without local truth wiring |

### T5 `/static/helm-gap-analysis.html`

| Check | Result |
|-------|--------|
| Purpose | Gap analysis wall |
| Local Vite | Path returns **SPA index** (same ~520KB dashboard shell) — **not** a dedicated static gap page unless relay has it |
| Risk | Title in browser may be client-set; content may be wrong shell |

### T6 `http://127.0.0.1:8770/pert` (**best local truth wall**)

| Check | Result |
|-------|--------|
| Purpose | Runtime-truth PERT: leases, census, revenue, gateway, factories |
| Feed | `/api/helm/live` every 1.5s |
| Live sample | 4 SOAK leases ACTIVE (HASF/HCF/HRF/HSF-32); NS UNDEFINED; revenue $0; concurrency PER_TASK_LEASE |
| Prior audit | F-1 hardcoded “0 FABRICATED”; idle LEASE→COMPLETE; scope/census mismatch (see earlier PERT audit) |
| Status | **Most authoritative runtime visualization on the desk** |

### T7 Relay home

| Check | Result |
|-------|--------|
| Purpose | Entry / dashboard |
| Docs | Night Watch command pack expects split layouts of control/board/factoryverse |

### Epic Fury `:3003` (not in Chrome list)

| Check | Result |
|-------|--------|
| Purpose | Champion product UI |
| Relation | Product lane; Apple distribution still external hold; not HELM control plane |

---

## 4. Root fragmentation (why “integrate all” is required)

```text
┌─────────────────── Tailscale relay :3012 ───────────────────┐
│ control / board / coordination / factoryverse / gap static │
│  (relay-api + /data JSON; may lag Mac runtime)             │
└────────────────────────────────────────────────────────────┘

┌─────────────────── Mac local ──────────────────────────────┐
│ Vite :3012  ──proxy /api──►  backend.main :8000            │
│                              council / control-plane/*     │
│ helm_live_api :8770  ◄── PERT tab only (not proxied before)│
│ pert_server :8765    ◄── third PERT feed (legacy/parallel) │
│ Epic Fury :3003      ◄── product                           │
└────────────────────────────────────────────────────────────┘
```

**Three PERT-ish truths:**

1. `:8770/pert` + `/api/helm/live` — soak/leases/census (current Phase A)  
2. `:8000/api/v1/control-plane/pert` — control-plane PERT (SPA)  
3. `:8765/api/pert/data` — classic HAS PERT command center  

**Without integration, the wall can look “alive” on relay while local soak is the only real motion.**

---

## 5. Fixes already applied in-repo (this session)

`frontend/vite.config.ts` updated so **local Vite :3012** proxies:

| Path | Target |
|------|--------|
| `/api/helm/*` | `http://127.0.0.1:8770` |
| `/api/v1/helm/*` | `http://127.0.0.1:8770` |
| `/api/founder/*` | `http://127.0.0.1:8770` |
| `/pert` | `http://127.0.0.1:8770` |
| `/founder` | `http://127.0.0.1:8770` |
| `/api/*` (rest) | `http://127.0.0.1:8000` |

**Requires Vite restart** to take effect:

```bash
# stop the existing vite on 3012, then:
cd ~/hoch_agent_swarm/frontend
npm run dev -- --port 3012 --host 0.0.0.0
```

Then open:

- `http://10.0.0.10:3012/pert` → same wall as `:8770/pert`  
- `http://10.0.0.10:3012/api/helm/live` → live JSON  

---

## 6. Integration plan (ordered)

### P0 — Single operator entry (local)

1. **Restart Vite** with updated proxy (above).  
2. **Bookmark set (local LAN):**
   - `http://10.0.0.10:3012/` — SPA shell  
   - `http://10.0.0.10:3012/pert` — runtime PERT (after restart)  
   - `http://10.0.0.10:3012/api/v1/control-plane/status` — control-plane JSON  
   - `http://10.0.0.10:3003/` — Epic Fury only when working product  
3. **Do not** treat relay tabs as soak proof until relay is fed from the same `/api/helm/live` snapshot.

### P0 — Relay ↔ Mac truth sync

Relay factoryverse/control currently read **files under `/data`** on the VPS. To integrate:

```text
Mac soak / helm_live_api
  → write/push snapshot (helm_control_live.json, helm_factoryverse.json)
  → relay /api/factoryverse + /control poll those files
```

Implement (if missing) a **push** from Mac:

```bash
# pattern already on relay: POST /api/factoryverse/push
# Add: POST control live snapshot from:
#   curl -s http://127.0.0.1:8770/api/helm/live \
#     | curl -sS -X POST -H 'Content-Type: application/json' \
#       --data-binary @- \
#       https://hoch-relay-001.tail826763.ts.net:3012/api/... 
```

Wire a 15–30s timer in soak or daemon: **push only observed live JSON**, never invented fields.

### P1 — Collapse three PERT feeds to one authority

| Keep as authority | Demote |
|-------------------|--------|
| `helm_live_api` `/api/helm/live` + `/pert` | Cosmetic edges only |
| | SPA `control-plane/pert` must **embed or proxy** helm live, not a second graph |
| | `pert_server:8765` → mark LEGACY; link from SPA “legacy PERT” only |

SPA change sketch:

- Overview PERT tab: `fetch('/api/helm/live')` (via Vite proxy)  
- Or iframe: `/pert` full-bleed  

### P1 — Factoryverse local

1. Serve `helm-factoryverse.html` from Vite `public/` or proxy `/factoryverse` → relay when online.  
2. Implement `GET /api/factoryverse` on **:8000 or :8770** by projecting `census` + `scope.factories` from `/api/helm/live` so local never 404s.  
3. Prefer **live census rungs** over static `helm_factoryverse.json` for color (earning-only green).

### P1 — Gap analysis static

1. Place real `helm-gap-analysis.html` under `frontend/public/static/`.  
2. Or redirect `/static/helm-gap-analysis.html` → latest `coordination/goal/HELM_FULL_BUILD_STATUS_*.md` rendered.  
3. Ensure Vite does not SPA-fallback that path.

### P1 — Chrome workspace layout (operator)

**Recommended 3-tab operator set** (close the rest or pin):

1. **Truth:** `http://10.0.0.10:3012/pert` (or `:8770/pert`)  
2. **Control / council:** relay `/control` **or** SPA overview after feed binding  
3. **Product:** `:3003` only when Epic Fury work is active  

Optional 4th: relay factoryverse after sync is proven.

### P2 — PERT wall truth defects (from prior audit)

Still fix in `frontend_live/pert.html`:

1. Remove hardcoded `EVERY NODE OBSERVED · 0 FABRICATED`  
2. Idle LEASE → IDLE/UNK not COMPLETE  
3. Populate verdict commit/four fields or mark PARTIAL  
4. Unify scope vs census champions  
5. Reject illegal task statuses in API  

### P2 — Soak completion gate for UI claim

Do not declare “UI integrated” until Phase A seals PASS/FAIL and `/api/helm/live` shows:

- `observed_peak_concurrency` numeric (not UNKNOWN when soak has overlap)  
- leases release cleanly  
- Epic Fury distribution still BLOCKED_EXTERNAL  

---

## 7. Verify after Vite restart

```bash
# truth wall via SPA host
curl -sS -m 5 http://127.0.0.1:3012/api/helm/live | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['observed_at'], len(d.get('leases') or []))"

# PERT HTML via SPA host
curl -sS -m 5 -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3012/pert

# still must work direct
curl -sS -m 5 -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8770/pert
```

Chrome:

1. Hard-refresh all tabs (Cmd+Shift+R).  
2. Prefer `http://10.0.0.10:3012/pert` for LAN wall.  
3. Keep relay tabs only if you need remote phone/Tailscale viewing **after** sync.

---

## 8. Summary board

```text
CHROME TABS:              7 open (6 relay + 1 local PERT)
LOCAL TRUTH WALL:         :8770/pert  — LIVE (soak Phase A in flight)
RELAY WALLS:              :3012 control/board/factoryverse — separate authority
SPA :3012:                proxies council/control-plane; helm/live was 404 (proxy fix added)
EPIC FURY :3003:          product, not control plane
INTEGRATION STATUS:       PARTIAL — proxy glue landed; relay sync + SPA PERT binding remain
24/7 / SOAK:              still NOT AUTHORITATIVE_PASS (fresh Phase A running)
```

**Bottom line:** Your Chrome set is a **split-brain operator desk** (relay surfaces vs local HELM LIVE). The fix is not “more tabs” — it is **one truth feed (`/api/helm/live`) behind one host (`:3012`)**, relay push of that feed, and demoting legacy `:8765` / static factoryverse when they diverge.

---

## 9. Immediate operator actions (checklist)

- [ ] Restart Vite on 3012 to load new proxy  
- [ ] Open `http://10.0.0.10:3012/pert` and confirm FEED not FEED LOST  
- [ ] Confirm `curl :3012/api/helm/live` returns leases during soak  
- [ ] Pin 3-tab workspace; archive unused relay tabs until sync exists  
- [ ] After soak seals, push live snapshot to relay (or disable relay until then)  
- [ ] Complete PERT F-1..F-5 truth fixes  
- [ ] Project factoryverse API from helm live on local stack  

This document: `coordination/goal/CHROME_WINDOW_AUDIT_20260713.md`
