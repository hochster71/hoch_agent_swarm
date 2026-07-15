# HELM Goal + Voice Agent Gap Analysis

**As-of:** 2026-07-15  
**Doctrine:** no_fake_green · Runtime Truth · DOORSTEP founder-only  
**Related:** `docs/architecture/HELM_VOICE_EXECUTIVE_INTERFACE.md` · `docs/prompts/helm_voice_executive_commander.md` · `backend/voice/*`

---

## 1. What is the goal of HELM?

### Canonical North Star (goal engine)

From `coordination/goal/goal_state.json` (validator-backed; not marketing copy):

> **Build a governed autonomous factory that converts Michael Hoch's judgment into shipped, monetized products, while minimizing founder time and never representing unverified work as complete.**

Hierarchy:

| Layer | ID | Statement |
|-------|-----|-----------|
| Permanent North Star | NS | Governed autonomous delivery of monetized products with minimal founder intervention |
| Current terminal outcome | TO | Ship **one** monetizable factory product to production distribution and prove intake → DOORSTEP end-to-end |
| Current champion product | CP | **EPIC_FURY_2026** (replaceable proof product — never the permanent identity of the system) |

### What HELM *is* (role)

**HELM** (Hierarchical Executive Leadership Matrix / Navy steering persona) is the **executive + execution interface** for HOCH:

| Layer | Name | Role |
|-------|------|------|
| Umbrella | **HOCH** | Whole system |
| Governor | **HAS** | Safety, evidence, relay, autonomy policy |
| Mind | **BRAIN** | Multi-domain genes, convergence, gap analysis |
| Steering | **HELM** | Mission commander: intake → route → verify → brief → escalate |
| Makers | **Factories** | Domain production under governance |

HELM is **not** release authority. It does not clear production GO without Final Verifier evidence. It **reduces founder cognitive load** by speaking only from Runtime Truth.

### Current goal metrics (observed — may be STALE)

| Metric | Value (last observed engine state) | Truth class |
|--------|--------------------------------------|-------------|
| North star completion | 0.0 | COMPUTED (weight-sum of passed validators) |
| Champion product | EPIC_FURY_2026 | DECLARED |
| Critical path blocker | REQ-CP-SECURITY | OBSERVED in goal_state |
| Founder-only pending | REQ-TO-001, REQ-TO-002, REQ-CP-TESTFLIGHT, REQ-CP-APP_STORE_CONNECT | OBSERVED |
| Evidence coverage | 96.0 | COMPUTED |
| Verified founder-minutes / shipped $ | **null → UNKNOWN** | Not fabricated (no revenue + no minutes ledger) |
| Autonomous execution coverage | 0.0 | COMPUTED |

**Voice implication:** every factory voice agent must serve this north star — ship monetized, governed products with less founder time — **not** theatrical dashboards.

---

## 2. Where voice is today (honest baseline)

### LIVE (orchestration-backed)

| Surface | Status |
|---------|--------|
| `GET/POST /api/v1/helm/voice/*` on HELM LIVE + main API | LIVE |
| Executive brief, founder approvals, runtime, goal_status, repo (local git) | LIVE |
| STAGE_ONLY route/mission staging | LIVE |
| DOORSTEP block (deploy/spend/keys) | LIVE |
| UI: `/voice`, console, founder, helm wall | LIVE |
| Persona prompt for Grok Voice Agents | LIVE as doc |

### NOT LIVE

| Gap | Status |
|-----|--------|
| Per-factory voice agents (HASF/HMF/HRF dedicated) | **Missing** — only generic factory summary |
| HSF / HFF / HCF / HHF / HPF voice | **Missing** — most not even in code registry |
| Leadership desks beyond founder (CFO, CISO, product, council) | **Missing** |
| Calendar / email / Jira / remote GitHub | **Missing** (local git only; GH remote UNKNOWN) |
| Grok cloud tool binding | Founder config, not automated |
| Paid / multi-agent voice collaboration | OFF / Vision |
| Event narration on all walls | Partial (Phase 1 sidecar evidence; not factory-wide) |

### Factories: declared vs code-registered vs voice-ready

| Code | Name | Declared in docs | In `backend/factory/registry.py` | Dedicated Runtime Truth path | Dedicated voice agent |
|------|------|------------------|----------------------------------|------------------------------|------------------------|
| **HASF** | Application Software | Yes | **Yes** (`software`) | Yes (gene pool, convergence, gates) | **No** (generic only) |
| **HMF** | Music | Yes | **Yes** (`music`) | Yes (subfolder brain) | **No** |
| **HRF** | Research | Yes | **Yes** (`research`) | Yes (citation gates) | **No** |
| **HSF** | Storybook | Yes (`docs/factories/`, `hsf/`) | **No** | Partial product (Story Studio deploy path) | **No** |
| **HCF** | Cybersecurity | Yes (docs / control plane) | **No** as factory | Partial (conmon, security posture) | **No** |
| **HFF** | Finance | Yes (docs / connectors) | **No** | Partial (spend ledger, Stripe) | **No** |
| **HHF** | Home | Yes (HomeMesh) | **No** | Partial (homemesh APIs) | **No** |
| **HPF** | Prompt | Yes (prompt brain) | **No** as factory | Partial (prompt_brain, promptops) | **No** |
| HWF/HVF/HIF/… | Writing/Video/Image… | Architecture future | **No** | No | **No** |

**Critical truth:** You cannot ship a “LIVE factory voice agent” for HSF/HFF/HCF/etc. until each has **observable state** (status, blockers, evidence, DOORSTEP). Otherwise voice becomes theater.

---

## 3. Stakeholder leadership map — voice benefit vs gap

Leadership roles are **how the founder (and later operators) think**. Each needs a **persona + tool binding + truth sources**, not a separate LLM without evidence.

| Leadership area | Stakeholder questions voice should answer | Benefit if LIVE | Current voice coverage | Gap severity | Priority |
|-----------------|-------------------------------------------|-----------------|------------------------|--------------|----------|
| **Founder / CEO (HELM Commander)** | What’s green? What’s blocked? What needs me? Next $0 lever? | Highest — cuts cognitive load | Strong (brief, approvals, goal, priority) | Medium (staleness, no multi-source desk) | **P0** |
| **COO / Mission Control** | Critical path, task queue, leases, overnight execution | High — 24/7 ops without staring at panels | Partial (runtime, tasks, overnight) | Medium | **P0** |
| **HASF Product Lead** | Epic Fury / release gates, TestFlight, App Store, evidence missing | High — champion product | Weak (mission_status heuristic only) | **High** | **P0** |
| **HSF Product Lead** | Story Studio revenue, Stripe, deploy, orders | High — second product / cash path | **None** | **High** | **P0** |
| **CISO / HCF Lead** | Incidents, NIST/RMF, conmon, exposure, advisories | High — security is current critical path (REQ-CP-SECURITY) | Weak (generic security blob) | **High** | **P0** |
| **CFO / HFF Lead** | Spend today, revenue, founder-min/$, Stripe health | High — north star is monetized | Partial spend in live API; voice thin; $ metrics UNKNOWN honestly | **High** | **P1** |
| **Research Lead (HRF)** | Citation gate, novelty, reproducibility, dual-use | Medium–High — anti-hallucination domain | None dedicated | Medium | **P1** |
| **Music Lead (HMF)** | Convergence, originality, publish gate | Medium | None dedicated | Medium | **P1** |
| **Home / HHF Lead** | Devices, mesh, privacy, unknown MAC approvals | Medium | None (homemesh has APIs) | Medium | **P2** |
| **Prompt / HPF Lead** | Gene pool, champions, prompt QA, model routing | Medium | Via BRAIN ask path; not voice-bound | Medium | **P1** |
| **Council / Multi-model** | Quorum, verdicts, chain integrity | High for trust | Authority partial; council not voice | Medium | **P1** |
| **QA / Final Verifier** | Release GO/NO-GO, evidence chain | High before any ship | evidence_gaps only | **High** | **P0** |
| **Release / App Store** | Package ready? Founder gates? | High for TO | DOORSTEP refuse only | Medium | **P1** |
| **Legal / Compliance** | Licensing (HMF), App Store policy, dual-use (HRF) | Medium | None | Low–Med | **P2** |
| **Customer / Support** | External product voice | Out of scope until revenue product | None | Future | **P3** |

---

## 4. Where voice agents **most** benefit HELM (ranked)

### Tier A — Highest leverage (build next)

These cut founder minutes on the **actual critical path** and money path.

| # | Voice agent | Why it benefits HELM | Truth sources to bind (must exist or be built) | Mode |
|---|-------------|----------------------|------------------------------------------------|------|
| A1 | **Founder Morning Commander** (enhance existing) | Single spoken state of the swarm | goal_state, authority, doorstep, runtime, factories | READ_ONLY |
| A2 | **HASF / Epic Fury Release Officer** | Champion product is the terminal proof | App Store path, TestFlight, final verifier, mission ledger | READ_ONLY + DOORSTEP escalate |
| A3 | **HSF Revenue Officer** | Story Studio is monetization path | Stripe, Vercel deploy state, order/webhook evidence | READ_ONLY + DOORSTEP |
| A4 | **CISO / Security Officer** | Current critical path **REQ-CP-SECURITY** | conmon, control posture, jspace security findings, RMF | READ_ONLY + IR stage |
| A5 | **QA / Final Verifier Voice** | Blocks fake ship | Final verifier, evidence chain, soak packages | READ_ONLY |

### Tier B — Factory specialists (after truth surfaces)

| # | Voice agent | Factory | Key commands | Blocker today |
|---|'------------|---------|--------------|---------------|
| B1 | HASF Engineer | HASF | “What’s blocked in software convergence?”, “pytest gate?” | Need factory-scoped brief endpoint |
| B2 | HMF Producer | HMF | “Originality gate?”, “ready for human A/B?” | Same + audio judge honesty |
| B3 | HRF Scientist | HRF | “Citation failures?”, “dual-use review?” | Same + citation ledger |
| B4 | HSF Story Producer | HSF | “Orders last 24h?”, “webhook health?” | Register HSF in factory registry + Stripe truth |
| B5 | HFF Controller | HFF | “Spend vs revenue?”, “runway narrative from ledger only” | Finance factory contract + spend/revenue APIs |
| B6 | HCF Watch Officer | HCF | “Open alerts?”, “quarantine?” | Promote cyber from control-plane to factory contract |
| B7 | HHF Home Officer | HHF | “Unknown devices?”, “mesh health?” | HomeMesh voice binding |
| B8 | HPF Prompt Officer | HPF | “Thin classes?”, “champion drift?” | prompt_brain already rich — easy bind |

### Tier C — Collaboration / future

| # | Voice agent | Benefit | Risk if premature |
|---|-------------|---------|-------------------|
| C1 | Multi-agent table (Grok/Claude/GPT council spoken) | Cross-check decisions | Hallucinated consensus without chain |
| C2 | Calendar priority adjuster | Align missions to founder day | Wrong priority without calendar truth |
| C3 | Customer-facing product voice | Revenue UX | Brand/legal; not HELM ops |

---

## 5. Gap matrix by HELM area (voice benefit × readiness)

Legend: **Benefit** = value if done well · **Readiness** = truth sources today · **Voice now** = actual integration

| Area | Benefit | Readiness | Voice now | Gap | Recommended action |
|------|---------|-----------|-----------|-----|--------------------|
| HELM Executive / Founder desk | ★★★★★ | High | LIVE | Polish + reduce STALE | Keep improving brief; freshness SLAs |
| Mission / PERT / Roadmap | ★★★★★ | High | Partial | Per-mission briefs | `mission_status` + goal PERT voice |
| Runtime / Leases / Soak | ★★★★☆ | High | LIVE | Narration of events | Optional event-to-speech bus |
| Council / Authority chain | ★★★★☆ | Med-High | Partial | Spoken quorum | `council_status` command |
| HASF software factory | ★★★★★ | High | Generic only | Factory agent | `factory_brief?code=HASF` |
| HMF music factory | ★★★☆☆ | Med | None | Factory agent | Same pattern |
| HRF research factory | ★★★★☆ | Med | None | Factory agent + citation honesty | Same + citation UNKNOWN rules |
| HSF storybook | ★★★★★ | Med (product exists) | None | Registry + Stripe voice | Register HSF; bind deploy/revenue |
| HCF cyber | ★★★★★ | Med | Weak | Security officer voice | Bind conmon + jspace + control posture |
| HFF finance | ★★★★★ | Med | Weak | CFO voice | Bind spend_ledger + Stripe; keep $0 honest |
| HHF home | ★★★☆☆ | Med | None | Home officer | Bind homemesh approval queue |
| HPF prompt | ★★★☆☆ | High (data rich) | None | Easy win | Bind gene/champion/gap APIs |
| Final Verifier / Release | ★★★★★ | Med | Weak | Verifier voice | Bind FV + evidence chain |
| Stripe / Billing | ★★★★★ | Med | None | Revenue voice | Webhook + entitlement truth only |
| App Store / TestFlight | ★★★★☆ | Low-Med | None | Release voice | DOORSTEP + package checklist |
| GitHub remote CI | ★★★☆☆ | Low | Local git only | Remote UNKNOWN | Optional `gh` when authed |
| Jira | ★★☆☆☆ | Low | None | Later | Don’t invent tickets |
| Calendar / Email | ★★★☆☆ | Low | None | Later | Founder gate on data access |
| Multi-agent voice | ★★☆☆☆ | Low | Vision | Premature | After Tier A |

---

## 6. Target architecture: “voice everywhere” without fake green

```
                    Founder / Operators
                            │
              ┌─────────────┴─────────────┐
              │   Voice Channel (Grok /   │
              │   local TTS desk / phone) │
              └─────────────┬─────────────┘
                            │
                    HELM Voice Gateway
              /api/v1/helm/voice/*
              policy · sanitize · audit
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
   Leadership agents   Factory agents    Domain tools
   founder, ciso,      HASF HMF HRF      stripe, git,
   cfo, qa, ops        HSF HCF HFF…      homemesh, jspace
         │                  │                  │
         └──────────────────┼──────────────────┘
                            │
                    Runtime Truth only
              LIVE | STALE | BLOCKED | UNKNOWN
```

### Factory voice agent contract (every factory must implement)

Before a factory voice agent is marked **LIVE**:

1. **Identity** in factory registry (code, domain, title)  
2. **Observe()** → status, blockers, last evidence, freshness  
3. **Speech brief** with labels (never invent scores)  
4. **DOORSTEP map** (what voice must refuse)  
5. **Tests** that fail closed when sources missing  
6. **UI mount** only where that factory is operated  

### Leadership agent contract

Same as factory, plus:

- Role persona (calm, domain vocabulary)  
- Escalation matrix → founder DOORSTEP  
- Explicit “out of scope” list (e.g. CFO never deploys)

---

## 7. Completion roadmap (to “all factories + all leadership”)

### Phase V0 — Done

- Central HELM Voice Executive API + desk + founder/console/wall  
- Goal + local repo + DOORSTEP + stage-only  

### Phase V1 — Leadership core (P0) — **next**

| Deliverable | Outcome |
|-------------|---------|
| `GET /api/v1/helm/voice/factory/{code}` | Per-factory brief for HASF/HMF/HRF |
| `GET /api/v1/helm/voice/role/{role}` | founder, ciso, cfo, qa, ops |
| HASF Release Officer commands | Epic Fury / evidence gaps |
| CISO Officer commands | REQ-CP-SECURITY, conmon, posture |
| QA Verifier commands | Final verifier / chain |
| Mount voice on roadmap, pert, jspace, command UIs | Leadership surfaces |

### Phase V2 — Product & money factories (P0–P1)

| Deliverable | Outcome |
|-------------|---------|
| Register **HSF** in factory registry + observe path | Story Studio voice |
| Stripe/revenue voice (read-only) | HSF + HASF monetization truth |
| HFF Controller brief from spend_ledger | Honest $0 when zero |
| App Store / TestFlight checklist voice | DOORSTEP only |

### Phase V3 — Full factory roster (P1–P2)

| Deliverable | Outcome |
|-------------|---------|
| HCF as first-class factory + IR voice | Security factory |
| HHF homemesh voice | Home leadership |
| HPF prompt voice | Prompt leadership |
| HMF/HRF specialist commands | Domain gates spoken |

### Phase V4 — External desk (P1–P2)

| Deliverable | Outcome |
|-------------|---------|
| GitHub Actions status (when authed) | CI voice |
| Calendar (founder-gated) | Priority adjust |
| Email summaries (founder-gated) | Comms load |

### Phase V5 — Multi-agent voice (P3)

Only after V1–V2 truth bindings are solid.

---

## 8. Anti-patterns (do not do)

1. **One Grok agent per factory with no tools** → role-play, fake metrics.  
2. **Mark HFF/HCF “voice complete”** before registry + observe().  
3. **Speak revenue** without Stripe/ledger observation.  
4. **Auto-deploy / auto-spend** from voice.  
5. **Event spam TTS** on every heartbeat (rate-limit + severity already policy).  
6. **Hardcode Epic Fury or HSF as permanent North Star** (goal contract forbids).  

---

## 9. Success criteria for “voice complete across HELM”

| Criterion | Definition of done |
|-----------|-------------------|
| Coverage | Every **registered** factory has `factory_brief` LIVE or explicit UNKNOWN |
| Leadership | founder, ops, ciso, cfo, qa each have role brief LIVE |
| Declared-not-registered | HSF/HCF/HFF/HHF/HPF either registered+voiced **or** labeled PLANNED (not LIVE) |
| No fake green | Any offline source → UNKNOWN in speech |
| DOORSTEP | Deploy/spend/keys/sign never succeed via voice alone |
| Evidence | Per-phase `docs/evidence/runtime/voice-*.md` with test output |
| Founder load | Morning brief answers NS/TO/CP without opening >1 panel |

**Today’s honest scorecard:** Central commander ~**40%** of the *executive* surface; factory+leadership matrix ~**10–15%** of the *full* roster. Completing “all areas” is a multi-phase program, not a single paste into Grok Voice.

---

## 10. Immediate recommended sequence

1. **V1 factory endpoint** for HASF/HMF/HRF (code already registered).  
2. **V1 role endpoints** for founder / ciso / cfo / qa.  
3. **Register HSF** with observe() from Story Studio + Stripe evidence.  
4. **CISO voice** tied to REQ-CP-SECURITY (current critical path).  
5. Only then expand HFF/HCF/HHF/HPF as first-class factories.

This sequence maximizes north-star progress (security + champion product + revenue) rather than uniform but shallow “voice everywhere.”
