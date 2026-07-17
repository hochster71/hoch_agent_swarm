# Founder "First-Dollar" Action Packet

**Authored (UTC):** 2026-07-16 (host shell clock unavailable — bash was locked by the live Phase C soak, so the filename uses the session date with a 00:00:00Z placeholder time).
**Author:** HELM docs subagent (read-only pass; no runtime state touched).
**Doctrine:** NO FAKE GREEN — every claim below is bound to a file that exists. Time figures are **estimates**. Items I could not verify are marked **UNKNOWN**.

**Source data (verified, read-only):**
- `has_live_project_tracker/data/founder_handoff_queue.json` (read in full — 39 staged items)
- `has_live_project_tracker/data/operator_next_actions.json` (read in full — non-revenue: Phase 2 voice design)
- `docs/revenue/epic_fury_rebuild_verify.md` (exists — Epic Fury build evidence)

---

## TL;DR — Fastest path to first dollar

**Story Studio (HSF, web + Stripe) reaches the first dollar with the least remaining work.** Its entire upstream is already **DONE**: the Stripe **LIVE** account, the $19 / $12-mo catalog, and payouts are live (`ss-stripe-account-bootstrap` = DONE), and the storefront + buy loop are built (`hsf-story-studio-go-live`). The founder-approved go-live plan is **SIGNED** but **not yet executed** — no purchase/revenue event is recorded in the queue. Only deploy-plumbing plus one real test purchase remain, and there is **no App Store review gate**. Do Story Studio first.

**Epic Fury (HASF, iOS + RevenueCat) is second** because, even though the build compiles, it still needs the full ASC/RevenueCat chain **and** a multi-day Apple review before any IAP dollar can land. It also currently ships a **dummy** RevenueCat key (`docs/revenue/epic_fury_rebuild_verify.md`), so a real key + rebuild is mandatory before resubmit.

### Top 3 founder actions (in order)
1. **Provision Vercel KV + set Story Studio live env** (`STRIPE_SECRET_KEY` live, the two price IDs, `AUTH_SECRET`, `BASE_URL`) — the secret/infra gate. Maps to `ss-stripe-live` / `hsf-story-studio-go-live` (both SIGNED).
2. **Register the LIVE Stripe webhook (`/api/webhook`), deploy, then make ONE real $19 purchase → confirm unlock → refund** — this is the first-dollar proof. Same items.
3. **Sign the Apple Paid Apps agreement + confirm banking/tax** (`rev-ef-paid-agreement`, READY_FOR_FOUNDER) — start this in parallel; it's the irreducible gate that unblocks the entire Epic Fury revenue chain.

---

## Evidence-integrity note (NO FAKE GREEN)

Nearly every monetization item points its `blocking_evidence` at a playbook under `docs/revenue/` — e.g. `STORY_STUDIO_GO_LIVE_NOW.md`, `epic_fury_pathB_resubmit_plan.md`, `FIRST_DOLLAR_PLAN.md`, `story_studio_go_live.md`, `story_studio_stripe_spec.md`, `stripe_setup_steps.md`, `epic_fury_iap_compliance.md`. **None of these files exist on disk.** The only file present in `docs/revenue/` is `epic_fury_rebuild_verify.md`. The actionable steps therefore survive **only in the queue's own inline `action` fields**, which I have transcribed verbatim below. Treat the "maps to" file paths as the queue's intended reference, not as a document you can currently open.

Two more truth flags:
- `ss-stripe-live` and `hsf-story-studio-go-live` are status **SIGNED** (founder approved the plan) but their execution sub-steps are **not** marked DONE — **first dollar has not actually been taken yet**.
- Epic Fury build v3 has a **dummy/test** RevenueCat key baked (`docs/revenue/epic_fury_rebuild_verify.md`, section 1: `NEXT_PUBLIC_REVENUECAT_IOS_KEY = BAKED (dummy/test key verified)`). A real live key + rebuild is required before resubmission or IAPs will not process.

---

## Already DONE / SIGNED — do NOT repeat

| Item id | What's done | Status | Evidence |
|---|---|---|---|
| `ss-stripe-account-bootstrap` | Stripe **LIVE** account `acct_1Tdge9DINF9KNAIC` active, charges+payouts enabled. Catalog: onestory `price_1TqjVNDINF9KNAICvsZ4Kl3t` ($19), creators `price_1TqjVNDINF9KNAICsqE8sy0G` ($12/mo) | **DONE** 2026-07-08 | queue `result` field |
| `r2-appstore-submit` | Epic Fury build 1.0-9 uploaded to TestFlight via Fastlane, distributed | **DONE** 2026-07-09 | queue `evidence` field |
| `rev-ef-iap-compliance-fix` | Payment split confirmed in code (web→Stripe, native iOS→RevenueCat/StoreKit); no 3.1.1 fix needed | **VERIFIED_IN_CODE** | `lib/purchases.ts`, `PaywallModal` |
| `rev-ef-model-price` | Monetization decision made = Path B (monetize now, resubmit) | **DECIDED_PATH_B** | — |
| `r2-security-signoff` | Epic Fury R2 security gate signed (0 real vulns) | **SIGNED** 2026-07-07 | `docs/evidence/products/epic-fury-2026/RELEASE_APPROVAL_20260707T155053Z.json` (referenced; existence UNKNOWN) |
| `ss-stripe-live`, `hsf-story-studio-go-live` | Go-live **plan approved** (build + catalog + payouts ready) | **SIGNED** — execution still pending (see "Do first") | inline action |
| `notify-channel`, `b-creators-auth-env`(AUTH_SECRET portion) | notify SIGNED; AUTH_SECRET folded into Story Studio env step below | mixed | — |
| Infra/neuro/security SIGNED set: `neuro-relay-redeploy`, `neuro-route-wire-deploy`, `neuro-brain-image-burst`, `neuro-changeboard-commit`, `arc-harden-apply`, `arc-cleanup-orphans`, `arc-macos-update`, `a-codeloop-wire`, `c-space-deploy`, `hrf-enable-code-mode`, `hif-doorstep-graduation` | founder-approved | **SIGNED** | not on first-dollar path |

**Superseded / do-not-duplicate:** `rev-ss-stripe-live` (READY_FOR_FOUNDER, "provision Story Studio Stripe live keys + payout bank") is superseded by `ss-stripe-account-bootstrap` (DONE) + `ss-stripe-live` (SIGNED). Do not redo the Stripe account or catalog — only the deploy/webhook/test-purchase steps remain.

---

## DO FIRST — unlocks revenue (Story Studio, the fastest first dollar)

All five map to the SIGNED items `ss-stripe-live` and `hsf-story-studio-go-live`. Their inline actions specify exactly these steps. Upstream (Stripe account, $19 catalog, payouts, storefront/buy-loop) is already DONE, so this is the shortest route to money.

| # | Founder action | Why founder-gated | Depends on | Est. time (estimate) | Maps to |
|---|---|---|---|---|---|
| D1 | **Provision Vercel KV** for Story Studio (the store the buy-loop reads/writes) | Creating cloud infra on the founder's Vercel account | — (upstream DONE) | ~5-10 min | `hsf-story-studio-go-live`, `ss-stripe-live` |
| D2 | **Set Story Studio live env in Vercel:** `STRIPE_SECRET_KEY` (live), price IDs (`price_1TqjVNDINF9KNAICvsZ4Kl3t` $19; creators `price_1TqjVNDINF9KNAICsqE8sy0G` $12/mo), `AUTH_SECRET` (long random), `BASE_URL` | Live secret handling — must be provisioned, never in chat | D1 | ~10 min | `ss-stripe-live`; also satisfies `b-creators-auth-env` (AUTH_SECRET) |
| D3 | **Register the LIVE Stripe webhook** → endpoint `/api/webhook`, capture `STRIPE_WEBHOOK_SECRET` into Vercel env | Money-side credential act on the live Stripe account | D2 (needs `BASE_URL`/deploy target) | ~5-10 min | `ss-stripe-live` |
| D4 | **Deploy** Story Studio to production | Publishing is a founder gate | D1-D3 | ~5 min | `hsf-story-studio-go-live` |
| D5 | **ONE real $19 purchase → confirm unlock → refund** | Taking real money is the irreducible founder act; this is the first-dollar proof | D4 | ~10 min | `ss-stripe-live` |

**Outcome of D5 = the first-dollar loop is proven.** (The self-test purchase is refunded net-zero; the first *retained* dollar arrives with the first real customer once the storefront URL is shared.)

Storefront/buy-loop code referenced as built: `public/index.html`, `api/save-story.js`, `api/download.js` (per `hsf-story-studio-go-live` action; file existence not independently verified — **UNKNOWN**).

---

## THEN — App Store / subscriptions (Epic Fury Path B)

Sequenced after Story Studio because it carries a multi-day Apple review before any dollar. All items below are **READY_FOR_FOUNDER** unless noted. The chain is strictly dependency-ordered.

| # | Founder action | Why founder-gated | Depends on | Est. time (estimate) | Maps to |
|---|---|---|---|---|---|
| T1 | **Sign the Paid Apps agreement + confirm bank account + tax forms** in App Store Connect | Legal agreement + banking/tax are irreducible to receive money | — (can start immediately, parallel with Story Studio) | ~15 min | `rev-ef-paid-agreement` |
| T2 | **Create the 2 auto-renewable subs in ASC:** `com.epicfury.dashboard.pro_monthly` ($4.99/mo) + `com.epicfury.dashboard.pro_annual` ($39.99/yr), localized name/desc, subscription review screenshot, generate **App-Specific Shared Secret** | Creating subs/prices is a founder money act | T1 (agreement must be accepted to submit subs) | ~30-45 min | `ef-b2-create-subs` |
| T3 | **Configure RevenueCat:** add iOS app (with Shared Secret), 2 products (same IDs), entitlement `pro`, offering `current` (monthly+annual), copy iOS public SDK key, set webhook → `/api/webhooks/revenuecat` with secret | RevenueCat account config + keys are founder credential acts | T2 (needs Shared Secret) | ~30 min | `ef-b3-revenuecat-config` |
| T4 | **Provide RevenueCat keys to build env:** set `NEXT_PUBLIC_REVENUECAT_IOS_KEY` + `REVENUECAT_WEBHOOK_SECRET` in Vercel + local build env (**replaces the dummy key currently baked** per `docs/revenue/epic_fury_rebuild_verify.md`) | Live keys are secrets the founder provisions | T3 | ~10 min | `ef-b4-provide-keys` |
| T5 | **Swarm rebuild** `ns-ef-rebuild` (produces the real-key binary) | Automated by the swarm once keys exist — **not** a manual founder gate, but only runs after T4 | T4 | ~10-20 min (automated; estimate) | `ef-b4-provide-keys` → rebuild; evidence pattern `docs/revenue/epic_fury_rebuild_verify.md` |
| T6 | **Upload new build, attach both subs to v1.0, resubmit** (pull v1.0 from review in ASC, attach subs, resubmit) | Upload + submit carry the founder's legal attestations | T5 + T2 | ~30 min | `ef-b6-upload-attach-resubmit` |
| T7 | **Apple review wait**, then live → first IAP dollar | Apple-side gate, outside founder control | T6 | ~1-3 days (**estimate**, Apple-dependent) | — |

---

## PARALLEL-OK (do alongside the above; none block Story Studio's first dollar)

| Item | Action | Status | Note |
|---|---|---|---|
| `rev-ef-paid-agreement` (= T1) | Sign Paid Apps agreement + banking/tax | READY_FOR_FOUNDER | Independent of Story Studio — start it now so the Epic Fury chain isn't idle |
| `apple-install-tools` | Install Icon Composer, SF Symbols 8, SF fonts, iPhone 17 / iPad Pro M5 bezels | READY_FOR_FOUNDER | Needed for icon/screenshots; not a first-dollar blocker. `docs/generated/apple/factory_apple_template_audit.md` (existence UNKNOWN) |
| `apple-liquid-glass-icon` | Build Epic Fury Liquid Glass layered icon; ship in **next** build (not this review) | READY_FOR_FOUNDER | Explicitly deferred to a later build by its own action text |
| `apple-screenshots-bezels` | Render 6-frame screenshot set; upload at next submission | READY_FOR_FOUNDER | Can be prepared while T7 review is pending |
| `cost-brevity-wire` | Wire caveman brevity into agent prompt behind `AGENT_BREVITY=1` | READY_FOR_FOUNDER | Cost hygiene, not revenue |

---

## LATER (not on the first-dollar path)

- **Factory doorstep graduations** (`hrf-`, `hmf-`, `hasf-`, `hsf-`, `hcf-`, `hff-`, `hhf-`, `hpf-`, `hcsf-`, `hbf-`, `haf-doorstep-graduation`) — org-level activate/publish approvals, READY_FOR_FOUNDER (a few SIGNED). The `hsf-` and `hasf-` graduations are effectively realized by shipping Story Studio and Epic Fury above; the rest are not first-dollar work.
- **`operator_next_actions.json`** recommends `facilitation-phase-2-design` (voice sidecar Phase 2, SAFE_DOC, no approval needed) — a design task, no revenue impact.
- Infra/security SIGNED items (`arc-*`, `neuro-*`, `a-codeloop-wire`, `c-space-deploy`, `hif-doorstep-graduation`, `hrf-enable-code-mode`) — already approved; not revenue.

---

## One-line sequence

**D1 → D2 → D3 → D4 → D5 (first dollar, Story Studio)**  ‖ start **T1** in parallel → **T2 → T3 → T4 → T5 → T6 → T7 (first IAP dollar, Epic Fury, after Apple review).**
