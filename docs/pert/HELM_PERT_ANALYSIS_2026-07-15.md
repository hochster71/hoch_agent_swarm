# HELM PERT Analysis

**As-of (observation):** 2026-07-15T17:12Z  
**Sources (LIVE probes):**  
- `GET http://127.0.0.1:8770/api/v1/helm/goal`  
- `GET http://127.0.0.1:8770/api/v1/helm/pert`  
- `GET http://127.0.0.1:8770/api/v1/helm/wall`  
- `GET http://127.0.0.1:8770/api/v1/helm/voice/factory/HCF`  
- `coordination/goal/goal_state.json` (engine file; **STALE** vs request time)

**Doctrine:** no_fake_green · VALIDATOR_NOT_RUN ≠ complete · STALE ≠ LIVE  

---

## 1. Goal of HELM (within HOCH)

**North star (permanent):**

> Build a governed autonomous factory that converts Michael Hoch's judgment into shipped, monetized products, while minimizing founder time and never representing unverified work as complete.

| Layer | Meaning | Weight contrib (engine) |
|-------|---------|-------------------------|
| **NS** | Permanent north star (2 reqs) | 9.0 → contributes **0.0** |
| **TO** | Ship one monetizable product intake→DOORSTEP (3) | 15.0 → **0.0** |
| **CP** | Champion product gates — **EPIC_FURY_2026** (10) | 40.0 → **0.0** |
| **ES** | Enabling system: council, dispatch, truth endpoints (4) | 15.0 → **0.0** |
| **GOV** | Authorization, no fake green, spend gates (6) | 25.0 → **0.0** |

**North star completion (computed):** **0.0%**  
**Evidence coverage field:** 96.0 (coverage of *declared* evidence artifacts — **not** completion)  
**Champion:** EPIC_FURY_2026  
**Hard constraint:** No fake green. No unevidenced completion. No autonomous execution beyond authorization.

**HELM's role in the graph:** executive + autonomy runner — mission, runtime truth, governance, routing — **not** release authority and **not** the permanent product identity.

---

## 2. Observed runtime PERT envelope (live wall)

| Surface | Observed | Label |
|---------|----------|--------|
| Goal file freshness | ~**74,600 s** (~20.7 h) old | **STALE** |
| PERT aggregate freshness | 0.0 s (recomputed at request) | LIVE probe |
| Runtime / leases | status **OK**, ~3 worker leases, capacity 4 | LIVE |
| Scheduler scope | **SOAK_IN_PROGRESS** | LIVE |
| 24/7 certification gate | **LOCKED** | LIVE |
| Integrity | **DEGRADED** (28 observed / 12 asserted nodes) | LIVE |
| Founder queue pending | **3** | LIVE |
| HCF posture | **76.9%**, gaps **AU-9, SI-4, SR-3** | PARTIAL |
| Verified settled revenue | **$0** (voice/ledger) | LIVE zero |
| Voice / ElevenLabs / launchd | Operational (enabling system, not NS completion) | LIVE ops |

---

## 3. Critical path (canonical engine order)

**Binding blocker (engine):** `REQ-CP-SECURITY`  
**Next recommended agent task:** same — highest-weight unresolved agent-actionable CP node.

All critical-path nodes currently report **`VALIDATOR_NOT_RUN`** (not PASS, not FAIL — **unproven**).

### 3.1 Critical path nodes (weight-ordered as stored)

| # | ID | Layer | W | Owner | State | Statement (short) |
|---|-----|-------|---|-------|-------|-------------------|
| 1 | **REQ-CP-SECURITY** | CP | 5 | agent | VALIDATOR_NOT_RUN | Epic Fury SECURITY gate |
| 2 | REQ-CP-SUBMISSION_PACKAGE | CP | 5 | agent | VALIDATOR_NOT_RUN | Submission package |
| 3 | REQ-ES-001 | ES | 5 | agent | VALIDATOR_NOT_RUN | Multi-adapter autonomous dispatch loop |
| 4 | REQ-GOV-002 | GOV | 5 | agent | VALIDATOR_NOT_RUN | Founder auth fully bound + one-shot |
| 5 | REQ-GOV-005 | GOV | 5 | agent | VALIDATOR_NOT_RUN | No fake green metrics |
| 6 | REQ-NS-001 | NS | 5 | agent | VALIDATOR_NOT_RUN | Founder not routine transport |
| 7 | REQ-TO-003 | TO | 5 | agent | VALIDATOR_NOT_RUN | Intake→DOORSTEP E2E proven |
| 8 | REQ-CP-APP_STORE_CONNECT | CP | 5 | **FOUNDER** | VALIDATOR_NOT_RUN | App Store Connect |
| 9 | REQ-TO-001 | TO | 5 | **FOUNDER** | VALIDATOR_NOT_RUN | Champion selected (process) |
| 10 | REQ-TO-002 | TO | 5 | **FOUNDER** | VALIDATOR_NOT_RUN | Champion ships to production |
| 11 | REQ-CP-MONETIZATION | CP | 4 | agent | VALIDATOR_NOT_RUN | Monetization gate |
| 12 | REQ-CP-SIGNING_READINESS | CP | 4 | agent | VALIDATOR_NOT_RUN | Signing readiness |
| 13 | REQ-CP-TEST | CP | 4 | agent | VALIDATOR_NOT_RUN | Test gate |
| 14 | REQ-ES-003 | ES | 4 | agent | VALIDATOR_NOT_RUN | Adapter path under spend gate |
| 15 | REQ-GOV-003 | GOV | 4 | agent | VALIDATOR_NOT_RUN | Mock cannot make quorum |
| 16 | REQ-GOV-004 | GOV | 4 | agent | VALIDATOR_NOT_RUN | Spend gate refuse capability |
| 17 | REQ-GOV-006 | GOV | 4 | agent | VALIDATOR_NOT_RUN | Tests read real files |
| 18 | REQ-NS-002 | NS | 4 | agent | VALIDATOR_NOT_RUN | Minutes-per-dollar measured |
| 19 | REQ-CP-TESTFLIGHT | CP | 4 | **FOUNDER** | VALIDATOR_NOT_RUN | TestFlight |
| 20 | REQ-CP-BUILD | CP | 3 | agent | VALIDATOR_NOT_RUN | Build gate |
| 21 | REQ-CP-PRIVACY | CP | 3 | agent | VALIDATOR_NOT_RUN | Privacy gate |
| 22 | REQ-CP-STORE_METADATA | CP | 3 | agent | VALIDATOR_NOT_RUN | Store metadata |
| 23 | REQ-ES-002 | ES | 3 | agent | VALIDATOR_NOT_RUN | Single spawn point for model CLIs |
| 24 | REQ-ES-004 | ES | 3 | agent | VALIDATOR_NOT_RUN | Council state endpoint truth |
| 25 | REQ-GOV-001 | GOV | 3 | agent | VALIDATOR_NOT_RUN | One H1 auth-eligible candidate |

**Founder-only pending (metrics list):**  
`REQ-TO-001`, `REQ-TO-002`, `REQ-CP-TESTFLIGHT`, `REQ-CP-APP_STORE_CONNECT`

---

## 4. Dependency logic (network view)

```
                    ┌────────────── NS (governance of load) ──────────────┐
                    │  NS-001 founder≠transport   NS-002 $/min measured   │
                    └─────────────────────┬───────────────────────────────┘
                                          │
         ┌────────────────────────────────┼────────────────────────────────┐
         ▼                                ▼                                ▼
   ┌── GOV ──┐                      ┌── ES ──┐                       ┌── TO ──┐
   │ auth    │                      │ multi- │                       │ select │
   │ gates   │◄────────────────────►│ adapter│◄──────────────────────│ ship   │
   │ no fake │                      │ spend  │                       │ E2E    │
   └────┬────┘                      │ truth  │                       └───┬────┘
        │                           └───┬────┘                           │
        │                               │                                │
        └───────────────┬───────────────┴────────────────┬───────────────┘
                        ▼                                ▼
                 ┌──────────── CP: EPIC_FURY_2026 ────────────┐
                 │ SECURITY → BUILD → TEST → PRIVACY →       │
                 │ SIGNING → SUBMISSION → METADATA →         │
                 │ MONETIZATION → TESTFLIGHT → ASC           │
                 └───────────────────────────────────────────┘
```

**CPM reading (truthful):**

- There is **no proven critical-path length in calendar days** until validators run and produce PASS/FAIL with evidence.  
- Treating all nodes as `VALIDATOR_NOT_RUN` with zero slack on **unproven** work is correct: **slack is unknown**, not zero-green.  
- The **logical** binding constraint named by the engine is **SECURITY** (highest weight, agent-actionable, first on critical_path list).  
- **Founder** nodes (TestFlight, App Store Connect, ship) sit on the **release tail** — they cannot clear until agent gates + packages exist.

### 4.1 Parallelism (where work can fan out)

| Parallel band | Nodes | Note |
|---------------|-------|------|
| **Security / posture** | REQ-CP-SECURITY + HCF AU-9/SI-4/SR-3 | Binding now |
| **GOV enforcement** | GOV-002…006, GOV-001 | Independent of App Store UI work |
| **ES autonomy** | ES-001…004 | Multi-adapter + spend + truth endpoints |
| **CP product package** | BUILD, TEST, PRIVACY, SIGNING, SUBMISSION, METADATA, MONETIZATION | After SECURITY opens |
| **Founder release** | TESTFLIGHT, APP_STORE_CONNECT, TO-002 | Serial after package ready |
| **Enabling (ops)** | Voice, launchd, Tailscale, ElevenLabs | **Not** NS weight — reduces founder minutes (NS-001 direction) |

---

## 5. Duration estimates (labeled — not observed)

Classic PERT three-point **planning** estimates for **remaining work to clear validators** (hours of focused agent/founder effort). These are **planning figures**, not runtime measurements.

| Band | Optimistic | Most likely | Pessimistic | PERT E = (O+4M+P)/6 |
|------|------------|-------------|-------------|---------------------|
| Close REQ-CP-SECURITY + HCF gaps (AU-9, SI-4, SR-3) | 8 | 24 | 60 | **~27 h** |
| CP package (BUILD→SUBMISSION+TEST+PRIVACY+SIGNING) | 20 | 48 | 100 | **~52 h** |
| ES multi-adapter + spend + council truth | 12 | 30 | 72 | **~34 h** |
| GOV auth/no-fake-green suite | 10 | 24 | 48 | **~26 h** |
| Monetization gate + ledger proof | 8 | 20 | 48 | **~23 h** |
| Founder TestFlight + ASC + ship (calendar-bound) | 4 | 16 | 40 | **~18 h** (founder) |

**Implied project E (if serial on CP after security):** roughly **~27 + 52 + 23 + 18 ≈ 120 h** of effort-equivalent, with ES/GOV largely **parallelizable** into the same window.

**Calendar span UNKNOWN** without resource calendar and validator automation rate.

---

## 6. Slack / risk

| Risk | Effect on critical path |
|------|-------------------------|
| Goal state **STALE** (~21 h) | Metrics may lag live soak/voice work |
| All reqs **VALIDATOR_NOT_RUN** | Zero NS completion is honest; risk is **stuck validators**, not hidden green |
| Integrity **DEGRADED** | Asserted nodes without observation inflate uncertainty |
| 24/7 gate **LOCKED** | Soak/cert path blocked from “certified” claim |
| Revenue **$0** | NS-002 / minutes-per-dollar stay **UNDEFINED** |
| Founder-only gates | Path ends in human bottleneck regardless of agent speed |

**Near-critical (high weight, not yet “first”):** SUBMISSION_PACKAGE, ES-001 multi-adapter, GOV-002 auth binding.

---

## 7. What recently completed work does *not* move NS %

These are **real** and useful, but **do not increment** `north_star_completion` until their validators PASS with evidence:

| Workstream | Status | PERT effect |
|------------|--------|-------------|
| HELM Voice Executive + factories/roles | LIVE ops | Supports NS-001 (less copy/paste) — not CP weight |
| ElevenLabs TTS + launchd + Tailscale phone | LIVE ops | Same |
| HCF posture 76.9% | PARTIAL | Feeds **REQ-CP-SECURITY** evidence package |
| Soak scheduler | IN_PROGRESS | ES/24-7 certification, still LOCKED |

---

## 8. Recommended sequence (next 5 moves)

| Pri | Owner | Action | Clears / advances |
|-----|-------|--------|-------------------|
| **P0** | Agent | Implement + **run validators** for **REQ-CP-SECURITY** using HCF gaps AU-9, SI-4, SR-3 | Binding blocker |
| **P0** | Agent | Refresh `goal_state` computation so freshness is LIVE | Kill STALE metrics |
| **P1** | Agent | REQ-CP-BUILD / TEST / PRIVACY package track (parallel after security package starts) | CP weight |
| **P1** | Agent | REQ-ES-001 multi-adapter autonomous loop + REQ-ES-004 council truth | ES weight |
| **P1** | Agent | REQ-GOV-005 + GOV-002 evidence (no fake green + auth bind) | GOV weight |
| **P2** | Founder | When package ready: TestFlight + App Store Connect | FOUNDER_ONLY |
| **P2** | Founder | First verified SETTLED revenue row (HSF or Epic Fury) | NS-002 becomes defined |

---

## 9. One-page critical path string

```
REQ-CP-SECURITY ──► CP product gates (BUILD/TEST/PRIVACY/SIGNING/SUBMISSION/…)
                 ──► MONETIZATION
                 ──► FOUNDER: TESTFLIGHT + APP_STORE_CONNECT
                 ──► TO-002 ship + TO-003 E2E intake→DOORSTEP
Parallel: ES multi-adapter/spend/truth + GOV auth/no-fake-green + NS minutes/$ instrumentation
Ops enablers (Voice/launchd/phone): reduce founder transport load (NS-001 direction) — not a substitute for validators
```

---

## 10. Verdict

| Question | Answer |
|----------|--------|
| Is HELM “done”? | **No.** NS completion **0.0** |
| Critical path tip? | **REQ-CP-SECURITY** (VALIDATOR_NOT_RUN) |
| Is the system idle? | **No** — runtime OK, soak in progress, voice LIVE, founder queue 3 |
| Fake green risk? | Managed if we keep validators unrun as unrun and STALE as STALE |
| Fastest agent lever? | Security gate validators + HCF control gaps |
| Fastest founder lever (later)? | TestFlight / ASC once package exists |

**Bottom line:** HELM’s PERT critical path is still the **Epic Fury champion gate stack**, blocked first at **SECURITY**, with **zero** weighted completion until validators execute successfully. Voice/ops infrastructure is an **enabling system** that reduces founder load; it does **not** by itself move north-star completion.
