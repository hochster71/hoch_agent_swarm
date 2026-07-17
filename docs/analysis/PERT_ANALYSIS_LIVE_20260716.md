# HELM — LIVE PERT ANALYSIS: Critical Path to the First Verified Settled Dollar

**Date:** 2026-07-16 (~08:31 CT / 13:31Z at snapshot)
**GOAL HELM finish line:** the first **VERIFIED SETTLED dollar** — a factory that has *earned* (rung 5 EARNING: a stranger has PAID and the balance transaction has SETTLED, verified against the account, not asserted).
**Doctrine:** NO FAKE GREEN. Estimates are labeled as estimates. Every node is owner-tagged. Overall GO is NOT declared while $0 has settled.
**Scope note:** "less the SOAK" — the running Phase C 24h soak is modeled as an in-flight background node, NOT a revenue blocker. It is not touched by this analysis.

---

## 0. Data provenance (read this first)

- **LIVE / authoritative source:** the goal engine on the Mac — `coordination/goal/goal_state.json` and `coordination/goal/mission_state.json` (both `goal_age_hours = 0.0` at snapshot), plus `coordination/products/product_registry.json`. These are what this PERT is built from.
- **Relay PERT wall** (`http://100.87.18.15:8770/api/v1/helm/pert`, `HELM_PERT_TRUTH`) is a **MIRROR**. Its runtime source reads UNPUBLISHED / stale — it is not the live critical path. Where it disagrees with the Mac goal_state, the Mac wins. Provenance flagged honestly per doctrine; the wall was not treated as truth here.
- **Duration numbers below are ESTIMATES** (optimistic O / most-likely M / pessimistic P), except the two hard anchors that are account-verified facts: Epic Fury's pending charge (`settles_at 2026-07-21`) and the soak seal clock (~14:45 CT today).

PERT expected time per node: **TE = (O + 4M + P) / 6.**

---

## 1. Ground truth (verified from the live files)

| Fact | Value | Source |
|---|---|---|
| North-star completion | **100.0%** | goal_state.metrics |
| Champion completion (EPIC_FURY_2026) | **100.0%** (computed from validators) | goal_state |
| Autonomous execution coverage | **100.0%** | goal_state |
| Evidence coverage | **100.0%** | goal_state |
| Agent-scope completion, every layer (NS/TO/CP/ES/GOV) | **100.0%** | goal_state.by_layer |
| Current critical-path blocker | **REQ-CP-APP_STORE_CONNECT** (owner FOUNDER_ONLY, state FAILED) | goal_state.critical_path |
| Founder-only pending | REQ-TO-002, REQ-CP-TESTFLIGHT, REQ-CP-APP_STORE_CONNECT | goal_state |
| Overall mission | **BLOCKED_EXTERNAL** | mission_state |
| Revenue | **NOT_STARTED — $0 verified settled** | mission_state.revenue (`settled_usd: 0.0`) |
| Epic Fury web charge | gross **$20.52** / net **$18.10**, `PENDING_SETTLEMENT`, **settles 2026-07-21**, `ch_3Tsv7qDK7Brrgheo1z3ksuF5` | product_registry |

The engineering areas (Engineering, Testing 23/23, Security PASS/NIST 100%, Evidence, Runtime Truth) are all VERIFIED. The **entire remaining critical path is FOUNDER + EXTERNAL**. No agent node remains on any revenue path.

---

## 2. Node lists to the first settled dollar (both revenue paths)

Owner legend: **[A] = AGENT (DONE)** · **[F] = FOUNDER** · **[X] = EXTERNAL**. Durations are ESTIMATES in hours unless noted; settlement in days.

### PATH A — Story Studio (HSF) WEB · $19 one-time / $12-mo · Stripe · NO Apple review

| # | Node | Owner | O | M | P | TE | Deps |
|---|---|---|---|---|---|---|---|
| A0 | Buy-loop code complete (store.js + api routes; 10/10 mocked-green) | **[A] DONE** | — | — | — | 0 | — |
| A1 | Provision live Stripe keys + payout **bank verification** | [F] | 0.5h | 1.0h | 4.0h | **1.42h** | A0 |
| A2 | Provision Vercel KV | [F] | 0.1h | 0.25h | 1.0h | **0.35h** | A0 |
| A3 | Set env (STRIPE_SECRET_KEY, price IDs, AUTH_SECRET, BASE_URL, STRIPE_WEBHOOK_SECRET) | [F] | 0.1h | 0.2h | 0.5h | **0.23h** | A1,A2 |
| A4 | Deploy to Vercel | [F] | 0.1h | 0.3h | 1.0h | **0.38h** | A3 |
| A5 | Register Stripe webhook endpoint | [F] | 0.1h | 0.25h | 1.0h | **0.35h** | A4 |
| A6 | One REAL purchase fires charge | [F]/[X] | 0.05h | 0.1h | 0.5h | **0.16h** | A5 |
| A7 | **Stripe settlement clock → SETTLED dollar** | [X] | 2d | 7d | 14d | **7.3d** | A6 |

**Path A founder active-work TE ≈ 2.9 hours** (A1–A6, sequential). The dominant terms are (i) founder **wall-clock** to sit down and do A1–A6 and (ii) the **Stripe settlement clock** A7. Epic Fury's own account settles a first charge in 7 days (07-14 → 07-21), giving an empirical anchor for A7 ≈ 7 days.
Caveat (from registry): the asserted live Stripe account + $19/$12 price IDs are **queue-asserted, UNVERIFIED** (not corroborated in any file on disk). If they are NOT actually live, A1 grows.

### PATH B — Epic Fury (HASF) APP STORE subscription · $19-mo · RevenueCat/ASC · Apple review

| # | Node | Owner | O | M | P | TE | Deps |
|---|---|---|---|---|---|---|---|
| B0 | Engineering / Security / Evidence complete | **[A] DONE** | — | — | — | 0 | — |
| B1 | Apple **Paid Apps** agreement + banking/tax | [F] | 0.5h | 2.0h | 8.0h | **2.75h** | B0 |
| B2 | Create subscriptions in App Store Connect (REQ-CP-APP_STORE_CONNECT) | [F] | 1.0h | 2.0h | 6.0h | **2.5h** | B1 |
| B3 | RevenueCat config + keys | [F] | 0.5h | 1.5h | 4.0h | **1.75h** | B2 |
| B4 | Upload build + resubmit (REQ-CP-TESTFLIGHT, REQ-TO-002) | [F] | 0.5h | 1.5h | 4.0h | **1.75h** | B3 |
| B5 | **Apple review** | [X] | 1d | 2d | 7d | **2.7d** | B4 |
| B6 | Production release live | [F]/[X] | 0.25h | 1.0h | 4.0h | **1.2h** | B5 |
| B7 | First real subscriber purchase | [X] | 0.5d | 3d | 10d | **3.75d** | B6 |
| B8 | **Apple/Stripe settlement clock → SETTLED dollar** | [X] | 7d | 14d | 30d | **15.2d** | B7 |

Path B carries the Apple review node (B5) AND Apple's slower payout cadence (B8), so it is structurally the **slowest** path. It is the source of the current live blocker (REQ-CP-APP_STORE_CONNECT).

### PATH A0′ — the passive anchor (already in flight, no new work)

| # | Node | Owner | Fact | Deps |
|---|---|---|---|---|
| Z1 | Epic Fury **web** charge already fired ($20.52 / net $18.10) | done | `CHARGE_PROVEN_SETTLEMENT_PENDING` | — |
| Z2 | **Stripe settlement clock → auto-promote to 5_EARNING** | [X] | **settles 2026-07-21** (verified vs account, not asserted) | Z1 |

This is a purely EXTERNAL, in-flight node requiring **zero founder action** — the same shape as the soak. Honestly, this is the **nearest-term** candidate for the first settled dollar.

---

## 3. Critical path & expected time-to-first-dollar

### Validating "Story Studio web is fastest"
Among paths that still require **build-out / provisioning**, **YES — Path A (HSF web) is fastest**: it has no Apple review node and rides Stripe's own faster settlement. Path B is dominated by B5 (Apple review) + B8 (slower Apple payout) and is weeks slower. Claim validated.

**BUT the honest, no-fake-green ranking of the first *settled* dollar:**

1. **NEAREST — passive:** Epic Fury web charge auto-settling **2026-07-21** (T+5 days). No founder, no code — pure clock, account-verified. *Not GO until it actually settles and is verified on 07-21.*
2. **FASTEST BUILD PATH — Path A (HSF web):** founder session (A1–A6) + Stripe settlement (A7 ≈ 7d).
3. **SLOWEST — Path B (Epic Fury App Store):** + Apple review + Apple payout cadence.

### Fastest actively-built critical path (Path A)
```
[A]Engineering DONE
      -> [F]Stripe live keys + payout bank  (A1, TE 1.4h)
      -> [F]Vercel KV                        (A2, TE 0.35h)
      -> [F]Env vars                         (A3, TE 0.23h)
      -> [F]Deploy to Vercel                 (A4, TE 0.38h)
      -> [F]Register Stripe webhook          (A5, TE 0.35h)
      -> [F/X]One real purchase              (A6, TE 0.16h)
      -> [X]STRIPE SETTLEMENT CLOCK ~7d      (A7, TE 7.3d)  ==> FIRST SETTLED DOLLAR
```
Critical-path length = founder active-work (~2.9h, gated on founder wall-clock) **+** settlement clock (~7d). The float on A2 (Vercel KV) is near-zero; the true driver is **founder wall-clock to start A1** and then **A7's settlement clock**.

### Expected time-to-first-settled-dollar (RANGE, estimate)
| Scenario | Path | Estimate |
|---|---|---|
| **Optimistic** | Path A0′ passive OR Path A with founder acting today + 2-day settle | **~2026-07-18 to 07-21** |
| **Most likely** | Epic Fury web charge settles as scheduled | **2026-07-21** (T+5d) |
| **Most likely — new build** | Path A: founder session within ~1 day + ~7d settle | **~2026-07-24 to 07-28** |
| **Pessimistic** | Founder delay + slow settle, or 07-21 charge slips | **early-to-mid August** |
| **Path B (App Store)** | + Apple review + Apple payout | **mid-to-late August** |

Dominant variables, in order: (1) **founder wall-clock** (the only human-gated term), (2) the **settlement clock** (Stripe ~7d anchored by Epic Fury; Apple longer), (3) Apple review (Path B only).

---

## 4. GO / NO-GO board

| Lane | Verdict | Basis |
|---|---|---|
| **Agent / Engineering** | 🟢 **GO** | north_star 100.0, champion 100.0, evidence 100.0, autonomous coverage 100.0; Testing 23/23, Security PASS / NIST 100%. All layers 100% agent-scope. Every revenue node is now [F] or [X] — **zero agent nodes remain.** |
| **Revenue** | 🔴 **NO-GO / BLOCKED_EXTERNAL** | mission_state Revenue = NOT_STARTED, `settled_usd: 0.0`. Gated entirely on FOUNDER (provision/deploy) + EXTERNAL (settlement / Apple review). $18.10 is PENDING, not settled. |
| **Overall GOAL HELM** | ⚪ **NOT YET EARNED** | No settled dollar exists. Per doctrine, overall GO is **NOT declared**. |

**Exactly what flips overall to GO:** the **first verified settled dollar** — the moment a factory reaches rung 5 EARNING (a real charge's balance transaction SETTLES and is verified against the account, not asserted). The nearest trigger is Epic Fury's web charge settling **2026-07-21**; the fastest *newly-built* trigger is Path A (HSF web) completing founder provisioning + Stripe settlement.

### In-flight background node (off the revenue critical path)
```
[X] Phase C 24h SOAK  — latest run HELM-SOAK-24H-20260715T194547Z
    started 2026-07-15 19:45:47Z  ->  seals ~2026-07-16 19:45:47Z (~14:45 / 2:45pm CT today)
    Status: RUNNING. Do NOT disturb.  NOT a revenue blocker — a governance/reliability gate.
    Product dispatch (HFF/HMF/HSF new missions) is queued to begin only AFTER the soak seals.
```
The soak is modeled here exactly as Epic Fury's settlement clock is — a passive external node the founder does not have to work, sealing this afternoon, sitting **beside** the revenue path rather than on it.

---

## 5. Critical-path diagram (fastest path to first settled dollar)

```
                          GOAL HELM = first VERIFIED SETTLED dollar
                                          |
   [A] Engineering/Sec/Evidence 100% DONE (no agent work left)
                                          |
          +-------------------------------+-------------------------------+
          |                               |                               |
   PASSIVE ANCHOR (Z)             PATH A — HSF web (FASTEST build)   PATH B — Epic Fury App Store
   Epic Fury web charge           [F] Stripe keys+bank               [F] Paid Apps + banking
   $20.52 already fired           [F] Vercel KV                      [F] ASC create subs  <== live blocker
          |                       [F] env vars                       [F] RevenueCat + keys
   [X] settle 2026-07-21          [F] deploy Vercel                  [F] upload + resubmit
          |                       [F] register webhook               [X] APPLE REVIEW ~2-7d
   ==> SETTLED $ (T+5d)           [F/X] one real purchase            [F] production release
   (most-likely first dollar)     [X] STRIPE SETTLE ~7d              [X] settle ~14-30d
                                          |                                    |
                                   ==> SETTLED $ ~07-24..07-28          ==> SETTLED $ ~mid-Aug
                                   (fastest NEW build path)             (slowest — Apple-gated)

   SOAK (in-flight, OFF path): seals ~2:45pm CT today. Not a revenue blocker.
```

---

*Generated read-only from live Mac goal_state / mission_state / product_registry. No soak, mission, key, or deploy actions taken. Overall GO withheld per NO FAKE GREEN — $0 has settled.*
