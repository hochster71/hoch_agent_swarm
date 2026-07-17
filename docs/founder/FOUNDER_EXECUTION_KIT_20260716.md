# FOUNDER EXECUTION KIT — Master Index

**The single front door.** Everything the founder must do to complete every open gate, in the right order, with one pointer per item to the detailed runbook.

**Authored (UTC):** 2026-07-16 (session date; host shell clock unavailable — the live Phase C soak holds the bash lock, so time is a placeholder).
**Author:** HELM founder-docs subagent — read-only pass, no runtime state touched, no mission dispatched, soak undisturbed.
**Doctrine:** NO FAKE GREEN. Every status below is bound to a file that exists. Estimates are labeled. Anything I could not corroborate on disk is marked **UNVERIFIED** or **UNKNOWN**. A gate that needs founder action is NEVER shown as done.

**Sources (read in full, read-only):**
- `has_live_project_tracker/data/founder_handoff_queue.json` — 41 staged items
- `coordination/products/product_registry.json` — current monetization rungs (authoritative for revenue truth)
- `backend/mission_control/factory_census.py` — the 0→5 ladder and NON-MONETIZED exemptions
- `docs/revenue/epic_fury_rebuild_verify.md` — Epic Fury build evidence
- Companion runbooks in this kit: `docs/founder/story_studio_go_live_runbook.md`, `docs/founder/epic_fury_appstore_runbook.md` *(authored alongside this index; if a runbook is not yet on disk, the queue's inline `action` field is the authoritative step list — see the Evidence-integrity note)*

---

## THE HONEST SCOREBOARD (read this first)

| Metric | Value | Source of truth |
|---|---|---|
| **Verified SETTLED revenue** | **$0.00** | No product shows `revenue_settled_usd > 0` in the registry |
| Real charge PROVEN, not yet settled | **$20.52 gross / $18.10 net** (Epic Fury, web/Stripe) | `EPIC_FURY_2026.revenue_trace = CHARGE_PROVEN_SETTLEMENT_PENDING` |
| Nearest EARNING dollar | **2026-07-21** (Epic Fury charge settles — passive, $0 founder work) | `settles_at: 2026-07-21` |
| Agent lane | **100% — everything the agent can do is staged/code-complete** | queue + `hsf_buyloop_impl_20260716T135932Z.md` |
| Factories EARNING (rung 5) | **0** | census verdict: "NO MONETIZED FACTORY IS EARNING" |
| Factories SELLABLE (rung 4) | **1** (Epic Fury; reachable Stripe checkout) | registry `monetization_rung: 4_SELLABLE` |

**Plain reading:** The build lane is finished. The only thing between HELM and its first *retained* dollar is founder-side account/credential/deploy clicks — plus one passive wait (7/21) that needs nothing at all.

---

## PRIORITIZED SEQUENCE TO FIRST (AND FASTEST) DOLLAR

### ★ PRIORITY 0 — passive, $0 work: watch the Epic Fury charge settle (2026-07-21)
A **real livemode Stripe charge already fired** on Epic Fury's web path: `ch_3Tsv7qDK7Brrgheo1z3ksuF5`, $20.52 gross / $18.10 net, first charge 2026-07-14. Stripe holds it PENDING until **2026-07-21**, when it promotes to `5_EARNING` **automatically, verified against the account — not asserted**. This is the likely **first earning dollar and it needs no founder action.** Just confirm settlement in the Stripe dashboard on/after 7/21.
→ Runbook: `docs/founder/epic_fury_appstore_runbook.md` (settlement-watch section). Registry: `EPIC_FURY_2026`.

### ★ PRIORITY 1 — fastest NEW build: Story Studio web go-live
Buy loop is **CODE-COMPLETE** (checkout → signed webhook → entitlement passes 10/10 mocked tests, evidence `docs/evidence/runtime/hsf_buyloop_impl_20260716T135932Z.md`). No App Store review gate. Remaining work is a **handful of founder clicks**: provision Vercel KV, set live Stripe env, register the live webhook, deploy, one real $19 purchase → confirm unlock → refund. Fewest remaining steps of any *new* revenue path.
→ Runbook: `docs/founder/story_studio_go_live_runbook.md`. Items: `hsf-story-studio-go-live`, `ss-stripe-live`.

### ★ PRIORITY 2 — Epic Fury App Store subscription path
The native iOS IAP path (separate from the Priority-0 web charge). Needs the full ASC + RevenueCat chain **and a multi-day Apple review** before any subscription dollar lands, and the current build ships a **dummy RevenueCat key** (`docs/revenue/epic_fury_rebuild_verify.md`) that must be replaced + rebuilt before resubmit.
→ Runbook: `docs/founder/epic_fury_appstore_runbook.md`. Items: `rev-ef-paid-agreement` → `ef-b2/b3/b4/b6`.

### ★ PRIORITY 3 — factory doorstep-graduations
Org-level activate/publish approvals. **Most are premature** (see the honest breakdown below). Only HASF and HSF are tied to actual products; the rest need an upstream product/checkout first or are exempt. Do NOT treat these as one-click revenue.
→ Runbooks: HSF → Story Studio runbook; HASF → Epic Fury runbook; the rest have no runbook because there is nothing founder-actionable yet.

---

## MASTER GATE TABLE — every founder gate (41 items)

Status legend: **DONE** (executed, evidenced) · **SIGNED** (founder approved the plan; execution may still be pending) · **READY_FOR_FOUNDER** (waiting on the founder) · **DECIDED / VERIFIED_IN_CODE** (resolved in code, no further action).

### A. First-dollar path — Story Studio (web / Stripe)

| id | gate type | status | the ONE founder action | dependency | runbook |
|---|---|---|---|---|---|
| `ss-stripe-account-bootstrap` | monetization | **DONE** | none — Stripe LIVE acct + $19/$12 catalog live | — | story_studio |
| `ss-stripe-live` | monetization | **SIGNED** (exec pending) | Provision Vercel KV, set live Stripe env, register live webhook, deploy | ss-stripe-account-bootstrap | story_studio |
| `hsf-story-studio-go-live` | monetization | **SIGNED** (exec pending) | Deploy + make ONE real $19 purchase → confirm unlock → refund | ss-stripe-live | story_studio |
| `b-creators-auth-env` | secret_handling | **READY_FOR_FOUNDER** | Set `AUTH_SECRET` (+ optional mailer) in Vercel for magic-link login | — | story_studio |
| `rev-ss-stripe-live` | monetization | **READY_FOR_FOUNDER** | *Superseded by ss-stripe-account-bootstrap + ss-stripe-live — do not redo catalog* | — | story_studio |

### B. Epic Fury App Store subscription path (native iOS / RevenueCat)

| id | gate type | status | the ONE founder action | dependency | runbook |
|---|---|---|---|---|---|
| `r2-security-signoff` | blocked_release | **SIGNED** | none — signed 2026-07-07 | — | epic_fury |
| `r2-appstore-submit` | blocked_release | **DONE** | none — build 1.0-9 on TestFlight | r2-security-signoff | epic_fury |
| `rev-ef-model-price` | monetization | **DECIDED_PATH_B** | none — Path B chosen | — | epic_fury |
| `rev-ef-iap-compliance-fix` | blocked_release | **VERIFIED_IN_CODE** | none — web→Stripe / iOS→StoreKit split confirmed | — | epic_fury |
| `rev-ef-paid-agreement` | monetization | **READY_FOR_FOUNDER** | Sign Paid Apps agreement + confirm bank + tax in ASC | — (start now, parallel) | epic_fury |
| `ef-b2-create-subs` | monetization | **READY_FOR_FOUNDER** | Create 2 auto-renew subs ($4.99/mo, $39.99/yr) + shared secret | rev-ef-paid-agreement | epic_fury |
| `ef-b3-revenuecat-config` | monetization | **READY_FOR_FOUNDER** | Configure RevenueCat products/entitlement/offering/webhook | ef-b2-create-subs | epic_fury |
| `ef-b4-provide-keys` | secret_handling | **READY_FOR_FOUNDER** | Set real `NEXT_PUBLIC_REVENUECAT_IOS_KEY` + webhook secret (replaces dummy) | ef-b3-revenuecat-config | epic_fury |
| `ef-b6-upload-attach-resubmit` | blocked_release | **READY_FOR_FOUNDER** | Upload rebuilt binary, attach subs to v1.0, resubmit | ef-b4 + swarm rebuild | epic_fury |
| `apple-install-tools` | blocked_release | **READY_FOR_FOUNDER** | Install Icon Composer, SF Symbols 8, SF fonts, bezels | — | epic_fury |
| `apple-liquid-glass-icon` | blocked_release | **READY_FOR_FOUNDER** | Build layered icon — *ship in NEXT build, not this review* | apple-install-tools | epic_fury |
| `apple-screenshots-bezels` | blocked_release | **READY_FOR_FOUNDER** | Render 6-frame screenshots; upload at next submission | apple-install-tools | epic_fury |

### C. Infra / security / change-board (already SIGNED — not on first-dollar path)

| id | gate type | status | the ONE founder action | dependency | runbook |
|---|---|---|---|---|---|
| `neuro-relay-redeploy` | blocked_release | **SIGNED** | none — approved 2026-07-09 | — | — |
| `neuro-route-wire-deploy` | blocked_release | **SIGNED** | none | — | — |
| `neuro-brain-image-burst` | monetization | **SIGNED** | none (paid burst GPU spend, approved) | — | — |
| `neuro-changeboard-commit` | blocked_release | **SIGNED** | none | — | — |
| `arc-harden-apply` | blocked_release | **SIGNED** | none | — | — |
| `arc-cleanup-orphans` | blocked_destructive_action | **SIGNED** | none | — | — |
| `arc-macos-update` | blocked_release | **SIGNED** | none | — | — |
| `a-codeloop-wire` | blocked_release | **SIGNED** | none | — | — |
| `c-space-deploy` | blocked_release | **SIGNED** | none | — | — |
| `notify-channel` | secret_handling | **SIGNED** | none | — | — |
| `cost-brevity-wire` | blocked_release | **READY_FOR_FOUNDER** | Wire brevity block behind `AGENT_BREVITY=1`; commit (cost hygiene, not revenue) | — | — |

### D. Factory doorstep-graduations (12) — READ THE HONEST BREAKDOWN BELOW

| id | gate type | status | the ONE founder action | actionable now? | runbook |
|---|---|---|---|---|---|
| `hasf-doorstep-graduation` | blocked_release | **READY_FOR_FOUNDER** | Realized by shipping Epic Fury (already SELLABLE, charge settling 7/21) | **YES — via Epic Fury** | epic_fury |
| `hsf-doorstep-graduation` | blocked_release | **READY_FOR_FOUNDER** | Realized by shipping Story Studio (buy loop code-complete) | **YES — via Story Studio go-live** | story_studio |
| `hff-doorstep-graduation` | blocked_release | **READY_FOR_FOUNDER** | Define + build a checkout FIRST — none exists | **NO — blocked on checkout** | — |
| `hmf-doorstep-graduation` | blocked_release | **READY_FOR_FOUNDER** | Define + build a checkout FIRST — none exists | **NO — blocked on checkout** | — |
| `hrf-doorstep-graduation` | blocked_release | **READY_FOR_FOUNDER** | No product defined yet — internal research engine | **NO — no product** | — |
| `hcf-doorstep-graduation` | blocked_release | **READY_FOR_FOUNDER** | No product defined ("to define") | **NO — no product** | — |
| `hhf-doorstep-graduation` | blocked_release | **READY_FOR_FOUNDER** | none — NON-MONETIZED (family ops) | **N/A — exempt** | — |
| `hpf-doorstep-graduation` | blocked_release | **READY_FOR_FOUNDER** | none — NON-MONETIZED (swarm-launch theater) | **N/A — exempt** | — |
| `hcsf-doorstep-graduation` | blocked_release | **READY_FOR_FOUNDER** | Internal compliance (ATO/ConMon posture) — not a saleable product | **NO — internal** | — |
| `hbf-doorstep-graduation` | blocked_release | **READY_FOR_FOUNDER** | Internal revenue-ops engine — not a saleable product | **NO — internal** | — |
| `hif-doorstep-graduation` | blocked_release | **SIGNED** | none — approved 2026-07-09 (infra truth engine) | already SIGNED | — |
| `haf-doorstep-graduation` | blocked_release | **READY_FOR_FOUNDER** | Internal autonomy orchestrator — not a saleable product | **NO — internal** | — |
| `hrf-enable-code-mode` | blocked_release | **SIGNED** | none — approved (code-mode flip for HRF) | already SIGNED | — |

---

## HONEST BREAKDOWN OF THE 12 DOORSTEP-GRADUATIONS (per the census)

The queue frames all twelve identically — "activate/publish/monetize." That framing is **misleading**; the census ladder tells the real story. **Most are premature.**

- **HASF — actually actionable (via Epic Fury).** Rung `4_SELLABLE`, reachable Stripe checkout, real charge settling 7/21. Graduation is real once that dollar settles. → Priority 0/2.
- **HSF — actually actionable (via Story Studio).** Rung `3_PRODUCTIZED_DEFINED_ONLY` today, but the checkout is **code-complete** (10/10 mocked tests) and needs only founder go-live. This is the one "defined" factory that becomes sellable with clicks, not new code. → Priority 1.
- **HFF, HMF — defined, NO checkout (premature).** Both are rung `3_PRODUCTIZED_DEFINED_ONLY`: a name + price only (`HFF_RUNWAY_PACKET` $15/mo, `HMF_CUE_LIBRARY` $9/mo), `checkout_url: null`, "no checkout built yet." "Graduation" means nothing until a checkout is **built** and the founder goes live. **Not one-click. Blocked on upstream build.**
- **HCF, HRF — artifacts, NO product (premature).** Rung ~2 `PRODUCES`. They generate deliverables but have **no product defined** (HCF is literally "to define"). Nothing to monetize yet. **Blocked on product definition.**
- **HHF, HPF — NON-MONETIZED / exempt.** By design in `factory_census.py` (`NON_MONETIZED = {"HHF","HPF"}`). Success = family utility / swarm visualization, not earning. These graduations **should not be on a revenue checklist at all.**
- **HCSF, HBF, HIF, HAF — internal engines, not saleable products.** ATO posture, revenue-ops, infra truth, autonomy orchestration. Their "go-live" is internal activation (HIF and HRF-code-mode are already SIGNED), not a stranger-facing checkout. **No first-dollar meaning.**

**Bottom line:** of 12 doorstep gates, exactly **2 (HASF, HSF)** map to a real first-dollar path; **4 (HFF, HMF, HCF, HRF)** are blocked on an upstream product/checkout; **2 (HHF, HPF)** are exempt; **4 (HCSF, HBF, HIF, HAF)** are internal. Do not pretend they are all one click.

---

## WHAT ONLY THE FOUNDER CAN DO vs. WHAT THE AGENT HAS STAGED

**Agent has already done / staged (100% of its lane):**
- Story Studio buy loop written and passing 10/10 mocked tests (`hsf/deploy/lib/store.js` + `api/*` routes; evidence `docs/evidence/runtime/hsf_buyloop_impl_20260716T135932Z.md`).
- Epic Fury build compiled, security-scanned (18→0), IAP compliance verified in code, uploaded to TestFlight.
- Every runbook, spec, and inline action transcribed and staged in the queue; all infra/neuro/security change-board items prepared and SIGNED.

**Only the founder can do (irreducible — permission system, not the agent):**
- Provision live payment credentials (Stripe live keys, Vercel KV, RevenueCat keys) and connect a payout bank.
- Sign legal agreements (Apple Paid Apps, banking/tax attestations, release approvals).
- Deploy to production and register live webhooks.
- Take the first real payment (the one purchase that proves the loop).
- Wait on Apple review (Epic Fury IAP path).
- Confirm the 7/21 Stripe settlement (passive — just look).

---

## ONE-LINE EXECUTION ORDER

**P0 (passive):** confirm Epic Fury Stripe settlement on **7/21** →
**P1:** Story Studio → KV → live env → webhook → deploy → 1 real $19 purchase = **first NEW-build dollar** →
**P2 (parallel from now):** sign Apple Paid Apps → subs → RevenueCat → real keys → rebuild → resubmit → Apple review →
**P3:** only HASF/HSF graduations are real; the other 10 are blocked-upstream or exempt.

---

### Evidence-integrity note (NO FAKE GREEN)
- Registry revenue figures are authoritative and self-verifying against the Stripe account; the queue's `status` fields reflect **plan approval**, not always execution. `ss-stripe-live` and `hsf-story-studio-go-live` are **SIGNED** but their execution sub-steps are **not** DONE — **the first Story Studio dollar has not been taken.**
- The Story Studio Stripe LIVE account / price IDs are **queue-asserted (`ss-stripe-account-bootstrap` = DONE) but UNVERIFIED on disk** — the cited `docs/revenue/*.md` setup files do not all exist; the registry flags this explicitly. Treat Stripe-live for HSF as **claimed, not proven**, until the founder confirms in the Stripe dashboard.
- Several `blocking_evidence` playbooks referenced by the queue (`STORY_STUDIO_GO_LIVE_NOW.md`, `epic_fury_pathB_resubmit_plan.md`, `FIRST_DOLLAR_PLAN.md`, etc.) are **not on disk**; the queue's inline `action` fields are the authoritative step source, and this kit's two companion runbooks consolidate them.
