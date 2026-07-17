# plan.md — HELM UI Implementation Plan

## Context

- **Baseline:** HELM_UI_BASELINE_RESET_FROM_ZERO_TOP_DOWN_DOCTRINE_DRIVEN
- **Current State:** `frontend_live/helm.html` exists — a single-page, event-driven, dark-cinematic dashboard with NIST 800-53 posture, North Star metric, factory grid, and live event stream. It is ALREADY doctrine-compliant (fail-loud, never shows stale data, motion is event-driven).
- **Target State:** `helm_ui_spec_v1.md` defines a full component architecture (HelmTopDownShell) with TopNavigation, RuntimeTruthStrip, LifecycleSpine, CommandBridge, ExperienceRail, FactoryVerseGrid, and CouncilPreview.
- **Authority:** READY_FOR_FOUNDER — no deployment until founder authorization.
- **Gate Rule:** This plan is AG IDE advisory. Founder must clear each stage at Doorstep.

---

## Stage 1 — Assessment & Mapping (Read-Only)

**Goal:** Map every existing element in `helm.html` to its spec counterpart. Identify what exists, what needs to change, and what is net-new.

### 1.1 Existing Element Map

| Existing Element (helm.html) | Spec Equivalent | Gap |
|-------------------------------|-----------------|-----|
| `<header>` brand + mode pill | TopNavigation + RuntimeTruthStrip | Need to split into two components; add nav items (Dashboard, Factory Verse, Council, Audit, Settings) |
| KPI row (CONCURRENCY, LEASES, ADAPTERS, SPEND, VERDICT) | SystemConfidence + TraceChain | Need to restructure into spec components; some KPIs move to rail, some stay in bridge |
| NORTH STAR card | CustomerValuePreview (variant) | North Star is founder-specific; keep as hero in bridge, but add to CustomerValuePreview rail module |
| SECURITY card (NIST 800-53) | TraceChain + EvidenceSparks | Security posture is evidence; should feed into EvidenceSparks module |
| Factory grid (4 factories) | FactoryVerseGrid (8 factories) | Need to add CORE, HPF, HFF; need ice overlay / frozen state; current grid has live/pass/blocked but no frozen language |
| EVENT STREAM | TraceChain + LiveMissionPulse | Event stream is raw trace; need to wrap in spec components with provenance hashes |
| TASKS table | DoorstepQueue + NextBestAction | Tasks table is task list; need to restructure into doorstep queue + prioritized NBA |
| HEARTBEAT canvas | LiveMissionPulse | Heartbeat visualizes event delta; needs to be integrated into mission pulse module |
| EPIC_FURY hold | DoorstepQueue | Already a doorstep gate; needs to be integrated into the queue system |
| `mode` pill (CONNECTING/COUNCIL EXECUTING/COUNCIL IDLE) | RuntimeTruthStrip | Truth strip needs to be sticky, include freshness, and have more state colors |

### 1.2 Net-New Components

1. **TopNavigation** — 56px sticky nav with blur backdrop. Does not exist in current `helm.html`.
2. **LifecycleSpine** — Left vertical phase indicator (Design → Build → Validate → Authorize → Operate). Does not exist.
3. **ExperienceRail** — Right 320px panel. Does not exist.
4. **FounderAuthorityBar** — Conditional amber bar for doorstep items. Does not exist.
5. **CouncilPreview** — Horizontal 12-seat row. Does not exist.
6. **NoFakeGreenPanel** — Educational overlay on hover. Does not exist.
7. **Relay200Preview** — Expanded mini-card/modal. Does not exist.

### 1.3 Assessment Deliverables

- [ ] Read `helm.html` completely and annotate every DOM element with its spec target
- [ ] Produce `helm_element_map.md` (Stage 1 output)
- [ ] Identify which API endpoints are currently consumed (`/api/helm/live`) and which new ones are needed per spec
- [ ] Flag any spec requirements that conflict with existing `helm.html` doctrine (e.g., fail-loud, event-driven motion)

**Authority Gate:** Stage 1 is read-only. No founder action needed. Can proceed autonomously.

---

## Stage 2 — API Contract Update (Spec)

**Goal:** The spec identified 8 endpoints. The current `helm.html` consumes only `/api/helm/live`. Define how to migrate or extend the API to satisfy the spec contract.

### 2.1 Endpoint Strategy

| Spec Endpoint | Current Equivalent | Strategy |
|--------------|-------------------|----------|
| GET /api/v1/helm/core/state | `/api/helm/live` (partial) | Split: extract core state fields into dedicated endpoint; or extend `live` to include all fields |
| GET /api/v1/helm/council/state | Not present | New endpoint; UI renders 12 seats in `ADVISORY` state until live |
| GET /api/v1/helm/relay-200/state | Not present | New endpoint; feeds Relay200Preview mini-card |
| GET /api/v1/helm/factory-verse/state | Partial in `live` (scope.factories) | Extend or split; needs frozen state, evidence counts, progress bars |
| GET /api/v1/helm/hcf/conmon/state | SECURITY section in `live` | Split: ConMon becomes dedicated endpoint |
| GET /api/v1/helm/provenance/clearance-state | `live` (verdict) | New dedicated endpoint; feeds TraceChain |
| GET /api/v1/helm/audit/status | SECURITY section in `live` | Split: audit status becomes dedicated endpoint |
| GET /api/v1/helm/runtime/status | Partial in `live` (concurrency, leases) | Split: runtime status becomes dedicated endpoint |

### 2.2 API Contract Deliverables

- [ ] Propose `/api/v1/helm/aggregate` (single endpoint returning all 8 contracts) OR keep 8 separate endpoints
- [ ] Document fail-closed behavior for each field (as defined in spec)
- [ ] Add `stale_after_seconds` to every endpoint response
- [ ] Add WebSocket/SSE capability for real-time updates (current `helm.html` polls every 1500ms)
- [ ] Produce `api_contract_v1.md` (Stage 2 output)

**Authority Gate:** This is a spec document. No founder action needed. Can proceed autonomously.

---

## Stage 3 — Component Architecture (Spec)

**Goal:** Define how the single `helm.html` file transforms into a component-based architecture. Since we're in a web context (likely static or Vite), decide on component technology.

### 3.1 Technology Decision

Current `helm.html` is vanilla HTML/CSS/JS. Options:

| Option | Pros | Cons |
|--------|------|------|
| A. Keep vanilla, refactor into ES modules | No build step, fast, existing code reusable | Manual component management |
| B. Web Components (custom elements) | Native, no framework, self-contained | Verbose, limited ecosystem |
| C. React/Vite | Rich component ecosystem, aligns with spec mental model | Build step, potential bloat |
| D. Preact/Vite | Lightweight React alternative | Still a build step |

**Recommendation:** Start with **Option A (vanilla ES modules)** for Stage 3-4, then migrate to **Option D (Preact/Vite)** if component complexity grows beyond 15 components. The existing `helm.html` is ~350 lines and highly optimized. Don't introduce a build step prematurely.

### 3.2 Component Breakdown

```
frontend_live/
├── helm.html                    (legacy, kept as backup)
├── helm_v2/
│   ├── index.html               (entry point, shell layout)
│   ├── css/
│   │   ├── shell.css            (layout, z-index, dark theme)
│   │   ├── components.css       (card, pill, ring animations)
│   │   └── states.css           (color semantics: slate/amber/blue/emerald/orange/rose)
│   ├── js/
│   │   ├── shell.js             (HelmTopDownShell: mounts all components, manages layout)
│   │   ├── api.js               (API client: polling, freshness, fail-loud)
│   │   ├── components/
│   │   │   ├── TopNavigation.js
│   │   │   ├── RuntimeTruthStrip.js
│   │   │   ├── FounderAuthorityBar.js
│   │   │   ├── LifecycleSpine.js
│   │   │   ├── CommandBridge.js
│   │   │   ├── ExperienceRail.js
│   │   │   │   ├── LiveMissionPulse.js
│   │   │   │   ├── DoorstepQueue.js
│   │   │   │   ├── EvidenceSparks.js
│   │   │   │   ├── TraceChain.js
│   │   │   │   ├── CustomerValuePreview.js
│   │   │   │   ├── NextBestAction.js
│   │   │   │   ├── SystemConfidence.js
│   │   │   │   └── APIContractStatus.js
│   │   │   ├── FactoryVerseGrid.js
│   │   │   ├── CouncilPreview.js
│   │   │   └── NoFakeGreenPanel.js
│   │   └── utils/
│   │       ├── stateColors.js   (color map: locked→slate, standby→amber, etc.)
│   │       ├── animations.js    (shared animation timing/easing)
│   │       └── accessibility.js (focus rings, aria-live, reduced motion)
│   └── assets/
│       ├── helm-sigil.svg
│       └── frost-texture.png    (for factory frozen overlay)
```

### 3.3 Stage 3 Deliverables

- [ ] Decide component technology (vanilla ES modules recommended)
- [ ] Produce component architecture document (`component_architecture.md`)
- [ ] Define component interface contract (props/events for each component)
- [ ] Produce wireframe mockups or ASCII layout diagrams for shell.js

**Authority Gate:** This is a spec document. No founder action needed. Can proceed autonomously.

---

## Stage 4 — Incremental Implementation (Build)

**Goal:** Implement the new architecture in stages, preserving the existing `helm.html` functionality at each step. Each stage produces a working file that can be opened in a browser.

### 4.1 Stage 4a: Shell + Theme

**Scope:** Create the top-level layout without any functional components. Just the grid structure, colors, and animations.

- [ ] `index.html` with shell layout (nav, truth strip, spine, bridge, rail)
- [ ] `shell.css` with dark theme, all state colors, animation keyframes
- [ ] `shell.js` with empty mount points for all components
- [ ] Test: Open `index.html` in browser. Should see dark layout with placeholder text in each region. No errors.

**Stage 4a Authority:** Build-only. No deployment. No founder gate.

### 4.2 Stage 4b: API Client + State Manager

**Scope:** Implement the API client with fail-loud behavior and freshness tracking. Connect to existing `/api/helm/live` as a single aggregate endpoint.

- [ ] `api.js` with `fetch()` wrapper, stale detection, retry logic
- [ ] `api.js` must fail-loud: if fetch fails, all components show "STALE" or "UNKNOWN"
- [ ] State manager that broadcasts updates to all components via `CustomEvent`
- [ ] Test: Open `index.html`. If API is reachable, data flows. If API is down, all components show fallback states.

**Stage 4b Authority:** Build-only. No deployment. No founder gate.

### 4.3 Stage 4c: Migrate Existing Components

**Scope:** Port the existing `helm.html` functional blocks into the new component structure. Preserve all existing behavior.

Migrate in this order:
1. **RuntimeTruthStrip** — Migrate the existing `mode` pill + header meta into the sticky truth strip. Add freshness indicator.
2. **CommandBridge** — Migrate the existing KPI row, NORTH STAR, SECURITY, HEARTBEAT, and TASKS table into the bridge area.
3. **FactoryVerseGrid** — Migrate the existing 4-factory grid. Add 4 new factories (CORE, HPF, HFF, HMF) with frozen state.
4. **TraceChain** — Migrate the existing EVENT STREAM into the trace chain component.

**Stage 4c Authority:** Build-only. No deployment. No founder gate.

### 4.4 Stage 4d: Net-New Components

**Scope:** Implement the components that don't exist in `helm.html`.

Implement in this order:
1. **TopNavigation** — Add nav items, active states, blur backdrop.
2. **LifecycleSpine** — Left vertical phase indicator. Connect to `helm_status`.
3. **ExperienceRail** — Right panel with Variant A (Executive Mission Pulse) as default. Implement all 8 modules.
4. **CouncilPreview** — Horizontal 12-seat row. All seats in `ADVISORY` state (blue outline).
5. **FounderAuthorityBar** — Conditional amber bar. Visible when doorstep has items.
6. **NoFakeGreenPanel** — Hover overlay explaining why something isn't green.
7. **Relay200Preview** — Mini-card / modal for Relay 200 state.

**Stage 4d Authority:** Build-only. No deployment. No founder gate.

### 4.5 Stage 4e: Integration & Polish

**Scope:** Connect all components, add animations, accessibility, reduced motion.

- [ ] All components respond to state updates via `CustomEvent`
- [ ] Animations: page entrance, state change, hover lift, stale pulse, blocker shake, success cascade, loading skeleton
- [ ] Accessibility: focus rings, aria-live, contrast ratios, keyboard navigation
- [ ] Reduced motion: `prefers-reduced-motion` disables all animations
- [ ] Mobile: responsive layout (rail collapses to 64px icon bar, spine hides, bridge goes full width)

**Stage 4e Authority:** Build-only. No deployment. No founder gate.

### 4.6 Stage 4f: Acceptance Testing

**Scope:** Verify all 12 acceptance criteria from the spec.

| AC | Test | Expected Result |
|----|------|-----------------|
| AC-01 | Manually set all 5 green fields to true | Only then does any element show green |
| AC-02 | Set `promotion_allowed=false` | GO CTAs show padlock, disabled |
| AC-03 | Block API response for 90s | Stale pulse appears, "Stale" label visible |
| AC-04 | Set `factory_work_frozen=true` | Factory cards show ice overlay, click shows modal, no navigation |
| AC-05 | Clear doorstep queue | Empty state shows relaxed icon, not "0" |
| AC-06 | Add evidence spark without `validator_sig` | Spark does not render |
| AC-07 | Set `provenance_hash` mismatch | Trace chain shows "Failed", not "Verified" |
| AC-08 | Set `council_live=false` | All seats remain blue outline, no green |
| AC-09 | Add item to doorstep queue | Founder Authority Bar appears |
| AC-10 | Scroll down page | Runtime Truth Strip remains sticky |
| AC-11 | View in grayscale / colorblind mode | All states distinguishable by icon, not just color |
| AC-12 | Enable `prefers-reduced-motion` | All animations disabled, all info preserved |

**Stage 4f Authority:** Test-only. No deployment. No founder gate.

---

## Stage 5 — Doorstep: Founder Review

**Goal:** Stage the working implementation for founder review. No deployment yet.

### 5.1 Staging Steps

- [ ] Open `helm_v2/index.html` locally in browser
- [ ] Take screenshots of each state: API up, API down, stale, frozen factories, doorstep items, all green
- [ ] Write `STAGE5_REVIEW.md` with: screenshot gallery, AC checklist results, known gaps, next steps
- [ ] Place in `artifacts/handoff/HELM_UI_STAGE5_REVIEW.md`
- [ ] Update coordination bus: `helm_v2` ready for founder review

### 5.2 Founder Gate

- [ ] Founder opens `helm_v2/index.html` (or screenshots if local file access is complex)
- [ ] Founder reviews visual system, animation, and truth state rendering
- [ ] Founder provides approval or requests changes
- [ ] If approved: drop `artifacts/handoff/HELM_UI_FOUNDER_APPROVED.txt`

**Authority Gate:** This IS a DOORSTEP action. AG IDE cannot approve. Must wait for founder.

---

## Stage 6 — Deployment (DOORSTEP — Founder Only)

**Goal:** Deploy the new HELM UI to replace or augment the existing `helm.html`.

### 6.1 Deployment Options

| Option | When to Use | Steps |
|--------|-------------|-------|
| A. Replace `helm.html` | Founder is confident in new UI | Rename `helm.html` to `helm_legacy.html`, copy `helm_v2/` to `frontend_live/helm/` |
| B. Side-by-side | Founder wants both available | Deploy `helm_v2/` to `frontend_live/helm_v2/`, add toggle in `helm.html` to switch |
| C. Feature flag | Founder wants gradual rollout | Add `?v2=1` query param to `helm.html` to load `helm_v2/` instead |

**Recommended:** Option C (feature flag) for the first deployment. Lowest risk.

### 6.2 Deployment Steps (AG IDE Prepares, Founder Executes)

1. AG IDE writes `DEPLOY_GUIDE.md` with exact commands
2. AG IDE stages the deploy in `artifacts/handoff/DEPLOY_HELM_UI.md`
3. Founder reviews guide and executes
4. Founder verifies deployment by opening the live URL
5. Founder drops `HELM_UI_DEPLOYED.txt` or `HELM_UI_ROLLBACK.txt`

**Authority Gate:** This IS a DOORSTEP action. AG IDE cannot deploy autonomously. Founder must execute.

---

## Stage 7 — Post-Deploy Validation (No Fake Green)

**Goal:** After deployment, verify the live UI behaves exactly as tested locally.

- [ ] Open live URL, verify API responses are fresh
- [ ] Verify all 12 ACs in production
- [ ] Run `frontend_live/helm_v2/test.html` (if test harness exists) or manual checklist
- [ ] If any AC fails: **ROLLBACK** immediately. No fake green.
- [ ] Write `POST_DEPLOY_VALIDATION.md` with results

**Authority Gate:** Validation is AG IDE's responsibility. Rollback decision is founder's.

---

## Timeline & PERT Estimates

| Stage | Optimistic | Most Likely | Pessimistic | PERT |
|-------|------------|-------------|-------------|------|
| 1 — Assessment | 30 min | 1 hr | 2 hr | 1.0 hr |
| 2 — API Contract | 1 hr | 2 hr | 4 hr | 2.2 hr |
| 3 — Architecture | 1 hr | 2 hr | 3 hr | 2.0 hr |
| 4a — Shell | 30 min | 1 hr | 2 hr | 1.0 hr |
| 4b — API Client | 1 hr | 2 hr | 3 hr | 2.0 hr |
| 4c — Migrate Existing | 2 hr | 4 hr | 6 hr | 4.0 hr |
| 4d — Net-New | 3 hr | 6 hr | 10 hr | 6.2 hr |
| 4e — Integration | 2 hr | 4 hr | 8 hr | 4.3 hr |
| 4f — Testing | 1 hr | 2 hr | 4 hr | 2.2 hr |
| 5 — Founder Review | — | founder-dependent | — | — |
| 6 — Deploy | — | founder-dependent | — | — |
| 7 — Validation | 30 min | 1 hr | 2 hr | 1.0 hr |

**Total AG IDE work (Stages 1-4f, 7):** ~22.9 hours (most likely)  
**Total with founder gates:** 22.9 + founder review time + deploy time

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| API endpoint 8-way split breaks existing `helm.html` | Medium | High | Keep aggregate endpoint running until v2 is deployed |
| Founder prefers existing `helm.html` and rejects v2 | Low | Medium | Option C (feature flag) allows easy toggle |
| Component complexity exceeds vanilla JS capabilities | Medium | Medium | Stage 3 decision point: if >15 components, migrate to Preact |
| Real-time SSE/WebSocket not available on current backend | High | Medium | Keep polling fallback (1500ms) as primary, SSE as enhancement |
| Animation performance degrades on older machines | Low | Low | Reduced motion support is AC-12; animations are CSS-only where possible |
| Accessibility audit fails | Medium | High | AC-11 and AC-12 are mandatory; test early and often |

---

## Current Stage

**Stage 0 — Plan Approved.**

Next: Stage 1 — Assessment & Mapping (can begin autonomously).

**Doorstep items awaiting founder:**
- None yet. First founder gate is at Stage 5 (review).

---

*Plan produced by Kimi K2.6 Swarm — HELM Parallel Design Swarm*  
*Timestamp: 2026-07-09T16:18:49-0500 (CDT)*  
*Authority: Advisory — implementation stages can begin, deployment awaits founder*
