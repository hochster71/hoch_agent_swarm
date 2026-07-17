# GAP ANALYSIS TO GOAL HELM — end-to-end, to the first VERIFIED SETTLED dollar

- **Author:** subagent (read-only pass), HELM doctrine = NO FAKE GREEN
- **Generated:** 2026-07-16 (~14:46Z), during an active 24h Phase C soak (not disturbed)
- **Scope:** read-only audit of live state; the only write is this document
- **Verification standard:** every claim below is cited to a file read this session. Estimates are labeled. Unknowns are written as UNKNOWN, not guessed.

---

## 1. Goal definition and the one metric that matters

**Goal HELM (canonical north star):** "Build a governed autonomous factory that converts Michael Hoch's judgment into shipped, monetized products, while minimizing founder time and never representing unverified work as complete." (`coordination/goal/goal_state.json` → `canonical_north_star`)

**The finish line is NOT "monetization configured."** It is the **first VERIFIED SETTLED dollar** — a factory that is actually EARNING, proven against a payment account rather than asserted. Doctrine, verbatim from the registry: *"A product exists when a stranger can name it, see a price, and reach a checkout. Anything less is an artifact."* (`coordination/products/product_registry.json` → `doctrine`) The census restates it: *"Artifacts are not products; a validated file that nobody can buy is a cost, not an asset."* (`backend/mission_control/factory_census.py`)

**The one metric that matters:** `revenue_settled_usd` > 0, verified against the merchant account.

- Verified live value: **$0.00.** `HochLedger.revenue_settled_usd() == 0`, `revenue_by_product() == {}` (executed this session against `backend/mission_control/hoch_ledger.py`).
- EARNING factories: **0 of 6 monetized** (`factory_census.py`).
- `verified_founder_minutes_per_shipped_dollar`: **UNKNOWN** — no founder-minutes ledger present and zero shipped revenue; the goal engine itself refuses to print a number here, calling it "a fabrication" (`goal_state.json` → `metric_unknown_reasons`). Minutes-per-dollar is therefore **UNDEFINED** until the first dollar settles.

---

## 2. Current-state scorecard

| Dimension | Value | Source |
|---|---|---|
| North-star completion | **100.0%** (agent-scope, validator-computed) | `goal_state.json` → `metrics.north_star_completion` |
| Champion completion (EPIC_FURY_2026) | **100.0%** | `goal_state.json` → `champion_product_completion` |
| Evidence coverage | **100.0%** | `goal_state.json` → `evidence_coverage` |
| Autonomous execution coverage | **100.0%** | `goal_state.json` → `autonomous_execution_coverage` |
| Verified settled revenue | **$0.00** | `hoch_ledger.py` (executed) |
| Minutes per shipped dollar | **UNKNOWN / UNDEFINED** | `goal_state.json` → `metric_unknown_reasons` |
| Current critical-path blocker | **REQ-CP-APP_STORE_CONNECT** | `goal_state.json` → `current_critical_path_blocker` |
| Founder-only pending | **REQ-TO-002, REQ-CP-TESTFLIGHT, REQ-CP-APP_STORE_CONNECT** | `goal_state.json` → `founder_only_actions_pending` |

**Critical reading of the 100%s:** the north-star/evidence/champion percentages are `100.0` *by construction* — the engine's rule is a "weight-sum of requirements whose validator EXECUTED SUCCESSFULLY against fresh evidence" **within agent scope** (`goal_state.json` → `computation_rule`). Every layer's `completion_pct_agent_scope` is 100.0, yet each still carries `founder_only_pending` items (TO, CP layers). **100% agent-scope completion coexists with $0 earned.** That is not a contradiction — it is precisely the gap this document measures: the agent lane is exhausted; the money lane is not open.

**Mission scorecard** (`coordination/goal/mission_state.json`, EPIC-FURY-2026):

- Engineering **VERIFIED/DONE** · Testing **VERIFIED** (23/23) · Security **VERIFIED** (NIST 100%, open=0/high=0) · Evidence **VERIFIED** · Runtime Truth **VERIFIED** (goal age 0.0h)
- Founder Review → **WAITING_FOUNDER**
- Apple Review → **Waiting on Founder** (TestFlight=UNKNOWN, ASC=UNKNOWN)
- Production Release → **WAITING_EXTERNAL**
- Revenue → **NOT_STARTED**, `settled_usd: 0.0`, detail "$0 verified settled revenue (expected until release earns)"
- **Overall Mission → BLOCKED_EXTERNAL** on `REQ-CP-APP_STORE_CONNECT`

**Factory census — the monetization ladder** (`factory_census.py`): declared **8** (6 monetized · 2 exempt: HHF, HPF) · productized **4** (HASF, HFF, HMF, HSF) · sellable **1** (HASF @ $19) · **EARNING 0**.

| Factory | Rung | Price | Earned | Blocker |
|---|---|---|---|---|
| HASF (Epic Fury) | SELLABLE | $19 | $0.00 | sellable, but nobody has paid — needs a buyer, not more code |
| HFF (Runway packet) | PRODUCTIZED | $15 | $0.00 | defined, NO CHECKOUT |
| HMF (Cue library) | PRODUCTIZED | $9 | $0.00 | defined, NO CHECKOUT |
| HSF (Story Studio) | PRODUCTIZED | $19 | $0.00 | defined, NO CHECKOUT (deploy scaffold inert) |
| HCF | PRODUCES | — | $0.00 | artifacts only, no product defined |
| HRF | PRODUCES | — | $0.00 | artifacts only, no product defined |
| HHF / HPF | EXEMPT | — | $0.00 | non-monetized by design |

---

## 3. What is DONE (agent lane)

**This session's agent-side deliverables (all on disk, verified):**

- `scripts/code_task_gate.py` + evidence doc `docs/evidence/runtime/code_task_gate_implementation_20260716T130030Z.md` — code-task readiness gate.
- Voice cost enforcement wired (voice sidecar Phase 2 cost brevity).
- **HSF Story Studio buy-loop code**, `hsf/deploy/` — Stripe Checkout + signed webhook + entitlement + KV store + auth routes. **10/10 mocked tests pass** (`hsf/deploy/test/buyloop.test.js`), including the full mocked end-to-end loop: checkout → webhook → entitlement true. Note: `hsf/deploy/lib/store.js` and the `api/*` routes that the product registry's `checkout_blocked_by` flagged as MISSING **now exist on disk** — the agent-side code blocker is closed; the registry note is stale on that specific point (deploy + live keys remain founder-gated, which is unchanged).
- 3 product definitions authored: HFF_RUNWAY_PACKET, HMF_CUE_LIBRARY, HSF_STORY_STUDIO (rung 3, `coordination/products/product_registry.json`).
- Census exemption for HHF/HPF; goal/mission state refresh (age 0.0h).

**Validated requirements (agent scope, `goal_state.json` `by_layer`):** NS 2/2 · TO 2/3 · CP 8/10 · ES 4/4 · GOV 6/6. Testing 23/23 (`.../REQ-CP-TEST-EPIC-FURY-...D4/test_results.json`). Security PASS, NIST posture 100% (`docs/products/epic-fury-2026/HASF_GATE_VERIFY.json`, `coordination/security/helm_control_posture.json`).

**One real charge already exists.** EPIC_FURY_2026 has a **real Stripe livemode charge**: gross **$20.52**, net **$18.10**, `stripe_charge_id: ch_3Tsv7qDK7Brrgheo1z3ksuF5`, state **PENDING_SETTLEMENT**, `settles_at: 2026-07-21`, rung `4_SELLABLE`, trace `CHARGE_PROVEN_SETTLEMENT_PENDING`. Its WEB revenue gate is configured and **fired** (`product_registry.json`). This is the single most advanced money-fact in the system: a proven charge whose net is held by Stripe, not yet settled.

---

## 4. THE GAP — every remaining item to the first settled dollar

Tag key: **[AGENT]** Claude can do · **[FOUNDER]** founder-only gate · **[EXT]** external (Apple / Stripe / settlement-clock).

There are **zero [AGENT]-tagged blockers** on any of the three paths below. Every remaining item is [FOUNDER] or [EXT]. That is the load-bearing finding (§5).

### Path 0 — Epic Fury WEB charge settling (already in flight, fastest to a settled dollar)

This path requires **no new build and no founder click.** The charge is already made.

1. **[EXT: settlement-clock]** Stripe balance transaction for `ch_3Tsv7qDK7Brrgheo1z3ksuF5` settles on **2026-07-21**. On settlement, the registry auto-promotes the product `4_SELLABLE → 5_EARNING`, "verified against the account, not asserted" (`product_registry.json` `rung_note`). Risk: refund/chargeback before settlement would void it.
2. **[AGENT, post-settlement]** Record the settled amount into `HochLedger.record_revenue(...)` so `revenue_settled_usd()` reflects it and the goal engine flips Revenue from NOT_STARTED. (Ledger write is agent-capable but must follow real settlement — writing it before 07-21 would be FAKE GREEN.)

> Honest note: **the literal first verified settled dollar is most likely this one, ~2026-07-21**, ahead of anything requiring new founder setup — provided the charge is not refunded. It is not on the App Store path at all; it is a web subscription that already charged.

### Path A — Story Studio (HSF) web checkout (fastest path the founder can *actively* open)

Agent code is complete and tested (§3). Remaining is deploy + live keys + one real purchase — all founder/external.

1. **[FOUNDER] `rev-ss-stripe-live`** — provision Story Studio **Stripe live keys + payout bank** (gate `blocked_monetization`, READY_FOR_FOUNDER). Note: a Stripe live account (`acct_1Tdge9DINF9KNAIC`) and $19/$12 price IDs are **ASSERTED DONE** in the queue item `ss-stripe-account-bootstrap` but are **UNVERIFIED** — they appear in no code/config on disk and the cited setup docs do not exist. Treat Stripe-live for HSF as **UNVERIFIED, not proven** (`product_registry.json` HSF `stripe_account_claimed`).
2. **[FOUNDER] `b-creators-auth-env`** — set the Creators-tier auth env/secret (gate `blocked_secret_handling`, READY_FOR_FOUNDER).
3. **[FOUNDER] deploy** — provision Vercel KV, set `STRIPE_SECRET_KEY`, price IDs, `AUTH_SECRET`, `BASE_URL`, `STRIPE_WEBHOOK_SECRET`, deploy `hsf/deploy/` to Vercel. Scaffold is INERT by design (returns 501 with no keys) until the founder flips live keys (`product_registry.json` HSF `checkout_blocked_by`).
4. **[EXT: Stripe]** one real test purchase → signed `checkout.session.completed` webhook writes entitlement to KV. Promotes HSF to sellable-proven.
5. **[EXT: settlement-clock]** first HSF charge settles → **EARNING**.

### Path B — Epic Fury (HASF) App Store distribution (the mission's declared champion path)

This is what `mission_state` tracks and what the current critical-path blocker sits on. It is the longest path (Apple review latency) but is the champion product.

1. **[FOUNDER] REQ-CP-TESTFLIGHT** + **`apple-install-tools`** — install Apple tooling, push a TestFlight build (gate `blocked_release`).
2. **[FOUNDER] `apple-liquid-glass-icon`**, **`apple-screenshots-bezels`** — App Store icon + screenshots (gate `blocked_release`).
3. **[FOUNDER] REQ-CP-APP_STORE_CONNECT** — the current critical-path blocker; complete App Store Connect listing/submission (gate `blocked_release`).
4. **[FOUNDER] `ef-b2-create-subs`** — create the subscription products (gate `blocked_monetization`).
5. **[FOUNDER] `ef-b3-revenuecat-config`** — configure RevenueCat (gate `blocked_monetization`).
6. **[FOUNDER] `ef-b4-provide-keys`** — provide the API keys (gate `blocked_secret_handling`).
7. **[FOUNDER] `rev-ef-paid-agreement`** — sign the Apple **Paid Apps agreement** + confirm banking/tax (gate `blocked_monetization`). Without this, Apple pays out $0 regardless of sales.
8. **[FOUNDER] `ef-b6-upload-attach-resubmit`** — upload/attach build and resubmit (gate `blocked_release`).
9. **[FOUNDER] REQ-TO-002** — remaining founder-only terminal-outcome requirement (`goal_state.json`).
10. **[EXT: Apple]** Apple review approval → production release (both `WAITING_EXTERNAL` in `mission_state`).
11. **[EXT: settlement-clock]** first App Store sale → Apple payout cycle → **EARNING**.

### Cross-cutting founder items in the queue

- **`cost-brevity-wire`** (gate `blocked_release`) — READY_FOR_FOUNDER.
- **11 `hXf-doorstep-graduation`** items (hrf, hmf, hasf, hsf, hcf, hff, hhf, hpf, hcsf, hbf, haf; gate `blocked_release`) — per-factory activate/publish/monetize graduations, all founder-only. These generalize the pattern beyond the two revenue paths.

**Queue totals (verified, `has_live_project_tracker/data/founder_handoff_queue.json`, key `staged`):** 41 staged — **22 READY_FOR_FOUNDER (all founder-only)**, 15 SIGNED, 2 DONE, 1 DECIDED_PATH_B, 1 VERIFIED_IN_CODE. All 22 ready items carry a founder gate: `blocked_release`, `blocked_monetization`, or `blocked_secret_handling`. **None is agent-actionable.**

---

## 5. The load-bearing finding

**The agent lane has no blocking gaps left to the door. Every remaining gap to the first settled dollar is founder-only or external.**

- Agent-fixable blockers remaining on the critical path to first dollar: **0.** (HSF buy-loop code is written and passes 10/10 mocked tests; product definitions exist; goal/mission/census are fresh; testing/security/evidence are VERIFIED.)
- Founder-only items ready and waiting: **22 of 22** READY_FOR_FOUNDER queue items, plus goal-engine `founder_only_actions_pending` REQ-TO-002 / REQ-CP-TESTFLIGHT / REQ-CP-APP_STORE_CONNECT.
- External dependencies: Apple review, Stripe live activation, and the **settlement clock** (EF web charge nets $18.10 held until **2026-07-21**).

The 100% north-star/evidence numbers are **true and simultaneously not money.** They measure agent-scope validator success, which is saturated. The distance to Goal HELM is now entirely a **founder-authorization + external-settlement** distance, not an engineering distance.

---

## 6. What Claude cannot do — and the exact minimal founder click-path

**Claude cannot, by policy and by capability:**

- **Configure live payment keys / secrets** — live `STRIPE_SECRET_KEY`, webhook secret, RevenueCat/Apple API keys. Handling live secrets is founder-gated (`blocked_secret_handling`); the agent must never take custody of production credentials.
- **Set up the payout bank / sign legal agreements** — Stripe payout bank, Apple Paid Apps agreement, banking/tax attestations. These are the founder's legal and financial identity; an agent cannot sign or bind them.
- **Deploy to production** — pushing `hsf/deploy/` live or releasing to the App Store requires the founder's Vercel/Apple accounts and the live secrets above.
- **Make a purchase / earn the dollar** — the settled dollar comes from a real buyer + a real settlement, not from any agent action. Writing revenue into the ledger before it settles would be FAKE GREEN.

These are also why the soak must not be disturbed and why the agent stays read-only here.

**Minimal founder click-path, per revenue path:**

- **Path 0 (Epic Fury web — do nothing, just watch):** confirm the $18.10 net for `ch_3Tsv7qDK7Brrgheo1z3ksuF5` settles on **2026-07-21** in the Stripe dashboard and is not refunded. On settlement, tell the agent to record it — first verified settled dollar, no setup required. *Estimated fastest path.*
- **Path A (Story Studio web — ~4 founder clicks to open a second earner):** (1) create/confirm Stripe live keys + payout bank [`rev-ss-stripe-live`]; (2) set Creators auth secret [`b-creators-auth-env`]; (3) set the six env vars and deploy `hsf/deploy/` to Vercel with KV; (4) run one real $19 test purchase and confirm the webhook writes entitlement. Then watch it settle.
- **Path B (Epic Fury App Store — the champion, longest):** in order — TestFlight build [`REQ-CP-TESTFLIGHT`/`apple-install-tools`] → icon + screenshots [`apple-liquid-glass-icon`, `apple-screenshots-bezels`] → App Store Connect listing/submit [`REQ-CP-APP_STORE_CONNECT`] → create subs [`ef-b2-create-subs`] → RevenueCat [`ef-b3-revenuecat-config`] → provide keys [`ef-b4-provide-keys`] → sign Paid Apps agreement + banking/tax [`rev-ef-paid-agreement`] → upload/attach/resubmit [`ef-b6-upload-attach-resubmit`] → await Apple approval → production release → first sale settles.

---

### Sources (all read this session)
`coordination/goal/goal_state.json` · `coordination/goal/mission_state.json` · `coordination/products/product_registry.json` · `backend/mission_control/hoch_ledger.py` (executed) · `backend/mission_control/factory_census.py` (executed) · `has_live_project_tracker/data/founder_handoff_queue.json` · `hsf/deploy/` (tree + `test/buyloop.test.js`, 10 tests) · `scripts/code_task_gate.py` · `docs/evidence/runtime/code_task_gate_implementation_20260716T130030Z.md`
