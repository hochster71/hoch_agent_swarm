# Epic Fury — App Store In-App-Subscription Monetization Runbook

**Purpose:** Tee up the Apple App Store IAP revenue path for Epic Fury so that only the founder's irreducible Apple-identity / legal / banking / live-keys / submit actions remain. Everything a docs subagent could pre-stage is staged here.

**Authored (UTC):** 2026-07-16 (host shell clock unavailable during a live Phase C soak; filename/date use the session date).
**Author:** HELM docs subagent — read-only pass, NO live Apple / App Store Connect / RevenueCat calls, NO keys set, NO deploy, NO spend.
**Doctrine — NO FAKE GREEN:** every claim is bound to a file that exists in this repo. Items the repo cannot corroborate are marked **UNVERIFIED**. Prices/times are what the repo records; where the repo disagrees with the mission brief I flag it.

**Apple Team ID:** `K34GR8P326` — verified: `docs/evidence/products/epic-fury-2026/security_scan_results_20260707.md` (Subject `Apple Distribution: Michael Hoch (K34GR8P326)`).

---

## 0-A. OBSERVED App Store Connect state (from founder's live screen, 2026-07-16)

Captured directly from the founder's ASC session — this is the current live truth, supersedes on-disk assumptions where it conflicts:

- **App:** Epic Fury 2026 · iOS · Apple ID `206366844` · **Version 1.0 "Ready for Distribution"** · **Build 8** · no App Clip.
- **⚠ App is REMOVED FROM SALE:** ASC shows *"This app was removed from sale from the App Store. Go to Pricing and Availability to add it back to the App Store."* The app is approved but **de-listed** — so nothing is buyable until it's re-listed.
- **Compliance nag:** *"Update Your Age Ratings Responses about Social Media"* — due **Sept 7, 2026** (App Information). Answer now to avoid a submission hold.
- **Screenshots:** iPhone **6.5" display** slot is the one that matters (only the first 3 are used on install sheets) — still to be supplied (= queue item `apple-screenshots-bezels`).
- **App Review Information:** *Sign-in required* — a demo username/password must be provided for review, plus contact info/notes.
- **Release:** choose manual vs automatic-after-approval at submit time.

### Fastest levers, given this state (two distinct goals — don't conflate)

**Goal 1 — get Epic Fury back on the store (AVAILABILITY, ~immediate, no new review):**
1. ASC → **Pricing and Availability** → add the app back to the App Store (re-list the already-approved v1.0 / build 8). Re-listing an approved version is typically effective within hours, **no App Review**. → App is downloadable again. *(This restores presence but earns $0 by itself — the iOS app is a free download; revenue is the IAP subs below.)*

**Goal 2 — turn on App Store revenue (IAP subscriptions, needs a review pass):**
2. Answer the **age-rating / social-media** questions (App Information).
3. Create the 2 auto-renewable subs (Monetization → Subscriptions) — see §1.
4. Wire **RevenueCat with a real key** + rebuild (build 8 ships a *dummy* key) — see §1 / `templates/revenuecat_config.md`.
5. Add the **6.5" screenshots**, set the **App Review sign-in** demo credentials.
6. Attach the subs to v1.0, upload the new build, **resubmit** → Apple review (~1–3 days est.).

> **Net:** Goal 1 is a near-immediate founder toggle (Pricing & Availability). Goal 2 is the full IAP chain in §1 and is what actually earns. Both are founder-only (Apple identity/legal/keys/submit); the engineering (v1.0 build is "Ready for Distribution") is already done. And remember Epic Fury's **web** dollar settles **7/21** regardless of any of this.

---

## 0. Two separate revenue paths — do not conflate them

Epic Fury has **two independent monetization routes**. This runbook is only about the second one.

| Path | Rail | Status | First dollar |
|---|---|---|---|
| **WEB upgrade** | Stripe (browser) | A **real livemode charge already fired**: `ch_3Tsv7qDK7Brrgheo1z3ksuF5`, **$20.52 gross / $18.10 net**, first charge 2026-07-14, Stripe holds it **PENDING → settles automatically 2026-07-21**. **Zero founder work** — just confirm in the Stripe dashboard on/after 7/21. | 2026-07-21 (passive) |
| **iOS in-app subscription** (this runbook) | Apple IAP / StoreKit, mediated by RevenueCat | Build compiles (v3) but ships a **dummy** RevenueCat key; needs the full ASC + RevenueCat + rebuild + resubmit + Apple review chain. | after Apple review (~1–3 days, estimate) |

Evidence for the web charge and 7/21 settlement: `docs/founder/FOUNDER_EXECUTION_KIT_20260716.md` (§Priority 0), `docs/journal/HELM_JOURNAL.md` (lines ~89–121).

> **Price note (UNVERIFIED / conflict):** The mission brief states Epic Fury is "$19/mo ($190/yr)". The repo's App-Store product definition (queue item `ef-b2-create-subs`) prices the **iOS subs at $4.99/mo and $39.99/yr**. The web Stripe charge that already fired was **$20.52 gross / $18.10 net** (`FOUNDER_EXECUTION_KIT_20260716.md`). The two rails are priced differently in the repo; the $19/$190 figure is **not corroborated on disk** for the App Store subs. Use the $4.99 / $39.99 App Store prices below unless the founder decides otherwise in App Store Connect (price is a founder choice made at sub-creation time).

---

## 1. Dependency-ordered founder sequence (iOS IAP path)

Each step lists **where** it's done, **what's needed**, and an **acceptance check**. Steps are strictly dependency-ordered: a later step cannot pass its acceptance check until the earlier one has.

Source of the step contents (transcribed from the queue's own inline `action` fields, since the referenced `docs/revenue/epic_fury_pathB_resubmit_plan.md` **does not exist on disk** — confirmed): `has_live_project_tracker/data/founder_handoff_queue.json` items `rev-ef-paid-agreement`, `apple-install-tools`, `apple-liquid-glass-icon`, `apple-screenshots-bezels`, `ef-b2-create-subs`, `ef-b3-revenuecat-config`, `ef-b4-provide-keys`, `ef-b6-upload-attach-resubmit`. Compliance rule: `docs/business/epic-fury-pricing-model.md`.

### S1 — Sign Paid Apps agreement + confirm banking/tax  `[FOUNDER-ONLY]`
- **Where:** App Store Connect → Business / Agreements, Tax, and Banking.
- **What's needed:** Accept the **Paid Applications agreement**; add a bank account for payouts; complete tax forms (W-9 / W-8 as applicable). Apple ID + 2FA required.
- **Acceptance check:** Paid Apps agreement shows **Active** and banking/tax rows show **Complete** in ASC. Subscriptions cannot be submitted for review until this is Active.
- **Queue item:** `rev-ef-paid-agreement` (READY_FOR_FOUNDER). Can start **immediately, in parallel** with everything else.

### S2 — Install Apple design tools on the Mac  `[MAC-RUN]`
- **Where:** The founder's Mac (macOS Sequoia+); downloads from `developer.apple.com/design/resources`.
- **What's needed:** Icon Composer, SF Symbols 8 (beta), SF Pro / SF Mono / New York fonts, iPhone 17 + iPad Pro (M5) bezels. Install the `.dmg`s.
- **Acceptance check:** Icon Composer opens and SF Symbols 8 launches on the Mac; bezel assets present locally.
- **Queue item:** `apple-install-tools` (READY_FOR_FOUNDER). Blocking-evidence file `docs/generated/apple/factory_apple_template_audit.md` is **UNVERIFIED** (not confirmed present). Not a first-review blocker.

### S3 — Produce icon + screenshots  `[MAC-RUN]`
- **Where:** Icon Composer + the founder's Mac (screenshot render); upload happens later at S8.
- **What's needed:**
  - **Icon:** Build the 3–4 layer Epic Fury Liquid Glass icon (light/dark/clear), export `Epic-Fury.icon` + flattened 1024 PNG. Per its own action text this icon **ships in the NEXT build, not this review** — so it does **not** gate the resubmit.
  - **Screenshots:** Render the 6-frame set in iPhone 17 / iPad Pro M5 bezels, captions sentence-case.
- **Acceptance check:** `Epic-Fury.icon` + 1024 PNG exist; 6 screenshots exist at App Store dimensions ready to upload in ASC.
- **Queue items:** `apple-liquid-glass-icon`, `apple-screenshots-bezels` (both READY_FOR_FOUNDER). Blocking-evidence `docs/generated/apple/epic_fury_liquid_glass_refresh.md` is **UNVERIFIED** (not confirmed present).

### S4 — Create the 2 auto-renewable subscriptions in ASC  `[FOUNDER-ONLY]`  ← depends on S1
- **Where:** App Store Connect → your app → **Subscriptions**.
- **What's needed:** Create a subscription group, then the two products with **exact product IDs**:
  - `com.epicfury.dashboard.pro_monthly` — **$4.99 / month**
  - `com.epicfury.dashboard.pro_annual` — **$39.99 / year**
  - Localized display name + description for each; a **subscription review screenshot**; generate the **App-Specific Shared Secret**.
- **Acceptance check:** Both products show status **Ready to Submit**; Shared Secret copied (needed at S5); review screenshot attached.
- **Queue item:** `ef-b2-create-subs` (READY_FOR_FOUNDER). Product IDs are the real IDs from the queue. (The short IDs `pro_monthly` / `pro_annual` in `docs/business/epic-fury-pricing-model.md` are the same products under their fully-qualified bundle-scoped names.)

### S5 — Configure RevenueCat  `[FOUNDER-ONLY]`  ← depends on S4 (needs Shared Secret)
- **Where:** RevenueCat dashboard.
- **What's needed:** Add the iOS app (paste the App-Specific **Shared Secret** from S4); create the 2 products with the **same** IDs as S4; create entitlement **`pro`**; create offering **`current`** containing monthly + annual; copy the **iOS public SDK key**; set the webhook to **`/api/webhooks/revenuecat`** with a secret.
- **Acceptance check:** RevenueCat shows both products, entitlement `pro`, offering `current`; iOS SDK key copied; webhook saved. (Use the template at `docs/founder/templates/revenuecat_config.md`.)
- **Queue item:** `ef-b3-revenuecat-config` (READY_FOR_FOUNDER).

### S6 — Provide RevenueCat keys to the build env  `[FOUNDER-ONLY]`  ← depends on S5
- **Where:** Vercel project env + local build env. **Never in chat.**
- **What's needed:** Set `NEXT_PUBLIC_REVENUECAT_IOS_KEY` (the iOS public SDK key from S5) and `REVENUECAT_WEBHOOK_SECRET`. This **replaces the dummy key currently baked** into build v3.
- **Acceptance check:** The rebuild (S7) bakes the **real** key — not `rc_dummy_active_key_test`. Current state per `docs/revenue/epic_fury_rebuild_verify.md`: `NEXT_PUBLIC_REVENUECAT_IOS_KEY = BAKED (dummy/test key verified)`, `REVENUECAT_WEBHOOK_SECRET = SET`. So the webhook secret is present but the **iOS key is still a dummy** and must be replaced.
- **Queue item:** `ef-b4-provide-keys` (READY_FOR_FOUNDER).

### S7 — Rebuild the binary with the real key  `[SWARM-AUTOMATED, then MAC-RUN archive]`  ← depends on S6
- **Where:** Rebuild task `ns-ef-rebuild` at `/Users/michaelhoch/epic-fury-build/epic-fury-2026`; then Xcode archive on the Mac.
- **What's needed:** Run the rebuild (Capacitor sync), then open Xcode → Archive.
- **Acceptance check:** Client bundle verification confirms the **real** RevenueCat key is baked (mirror of the v3 check that verified `rc_dummy_active_key_test` — must now show the live key). Xcode archive succeeds. Evidence pattern: `docs/revenue/epic_fury_rebuild_verify.md`.

### S8 — Upload build, attach subs to v1.0, resubmit  `[FOUNDER-ONLY]`  ← depends on S7 + S4
- **Where:** Xcode / Fastlane (upload) → App Store Connect (attach + submit).
- **What's needed:** Upload the rebuilt binary; in ASC **pull v1.0 out of review**, **attach both subscriptions** to the v1.0 version + the review submission, upload the 6 screenshots (S3), resubmit.
- **Acceptance check:** ASC shows the new build attached to v1.0, both subs attached to the version, submission state **Waiting for Review**.
- **Queue item:** `ef-b6-upload-attach-resubmit` (READY_FOR_FOUNDER). Prior upload precedent: build 1.0-9 was already uploaded to TestFlight via Fastlane (`r2-appstore-submit` = DONE).

### S9 — Apple review → live → first IAP dollar  `[APPLE-SIDE, outside founder control]`  ← depends on S8
- **Where:** Apple App Review.
- **What's needed:** Wait. Respond to any reviewer messages.
- **Acceptance check:** App + subs **Approved / Ready for Sale**; a real IAP purchase unlocks entitlement `pro`. This is the first App-Store IAP dollar. **Estimate ~1–3 days, Apple-dependent.**

### One-line sequence
**S1 (parallel: S2→S3) → S4 → S5 → S6 → S7 → S8 → S9.**
S1, S2, S3 can all begin immediately; S4 is the first hard gate (needs S1's agreement Active).

---

## 2. RevenueCat config template

A committed, placeholder-only template lives at **`docs/founder/templates/revenuecat_config.md`**. It enumerates the products, entitlement `pro`, offering `current`, webhook URL, and key **NAMES** (no secret values). Fill it in inside the RevenueCat dashboard at step S5. Summary of what it contains:

- Products: `com.epicfury.dashboard.pro_monthly`, `com.epicfury.dashboard.pro_annual`
- Entitlement: `pro`
- Offering: `current` (packages: monthly + annual)
- Webhook URL: `https://<APP_BASE_URL>/api/webhooks/revenuecat`
- Key names only: `NEXT_PUBLIC_REVENUECAT_IOS_KEY`, `REVENUECAT_WEBHOOK_SECRET`, App-Specific Shared Secret (from ASC)

---

## 3. IAP-compliance note (Apple Guideline 3.1.1)  — status: VERIFIED_IN_CODE

**Claim:** In-app (iOS) digital upgrades use **Apple IAP / StoreKit (via RevenueCat)**, and **Stripe is used only for the web** path — satisfying App Review Guideline **3.1.1** with no fix needed.

**Queue attestation** (`has_live_project_tracker/data/founder_handoff_queue.json`, item `rev-ef-iap-compliance-fix`, status **`VERIFIED_IN_CODE`**):
> "Confirmed in code: web->Stripe, native iOS->RevenueCat/StoreKit (lib/purchases.ts + PaywallModal). No 3.1.1 fix needed; keep the split."

**What the repo corroborates (cited):**
- **Policy is documented** — `docs/business/epic-fury-pricing-model.md` (titled "Epic Fury iOS In-App Purchase Compliance"): *"For in-app digital upgrades/unlocks on iOS, Epic Fury must use Apple In-App Purchase (IAP) via StoreKit rather than Stripe … RevenueCat may be used as a wrapper, provided it ultimately uses Apple IAP / StoreKit … Stripe may remain in use for web or other permitted commerce flows, but not for iOS in-app digital purchases."* Product IDs named: `pro_monthly`, `pro_annual`.
- **Both rails exist in the dependency tree** — `docs/evidence/business/epic-fury-full-code-audit.md` (Dependency Inventory) lists **`@revenuecat/purchases-capacitor` `^12.3.2`** (the native StoreKit wrapper) **and** **`stripe` `^22.0.2`** (web) in the `epic-fury-build` target. The Stripe usage in that audit is confined to **web API routes**: `app/api/stripe/checkout/route.ts`, `app/api/stripe/portal/route.ts` (all keys are mock placeholders `sk_live_xxx` / `sk_test_xxx` — no live keys). `docs/evidence/business/epic-fury-onboarding-audit.md` independently re-confirms deps `stripe` + `@revenuecat/purchases-capacitor` and "No secret leaks."

**UNVERIFIED-in-this-repo (honesty flag):** The exact files the queue cites for the verification — **`lib/purchases.ts`** and **`PaywallModal`** — are **not present in this HELM repo**. The Epic Fury application source lives in a **separate, un-mounted tree** at `/Users/michaelhoch/epic-fury-build/epic-fury-2026` (path per `docs/revenue/epic_fury_rebuild_verify.md`). So the precise line-level `platform === 'web' ? Stripe : RevenueCat` branch cannot be quoted from disk here. What **is** verifiable in-repo is: (a) the written 3.1.1 policy, (b) the presence of the RevenueCat-Capacitor native wrapper alongside a **web-only** Stripe surface, and (c) the queue's `VERIFIED_IN_CODE` attestation. The compliance posture is therefore **corroborated at the dependency + policy + attestation level**; the code-line quote is deferred to the external build repo.

**Bottom line:** No 3.1.1 remediation is required. Keep the split (web→Stripe, iOS→RevenueCat/StoreKit). The only iOS-side work is credential/config/rebuild/submit (Section 1), not a payment-routing change.

---

## 4. Who does what — irreducibly founder-only vs. just Mac-run

### Irreducibly FOUNDER-ONLY (Apple identity / legal / money / live secrets / submit) — no agent can do these
- **S1** Apple ID + 2FA login; accept **Paid Apps agreement**; **banking + tax** setup.
- **S4** Create the 2 subs + prices + generate **App-Specific Shared Secret** (a money act in ASC).
- **S5** RevenueCat account config (credential act).
- **S6** Provision **live keys** into the build env (secret handling — never in chat).
- **S8** **Upload + resubmit** — carries the founder's legal attestations.
- (Also: confirming the web charge settlement on 7/21 in the Stripe dashboard — trivial, passive.)

### Just MAC-RUN (on-device creative / install acts the founder performs, but not identity/legal gates)
- **S2** Install Icon Composer / SF Symbols 8 / fonts / bezels (`.dmg` installs).
- **S3** Build the Liquid Glass icon + render the 6 screenshots. (Icon ships in the **next** build, so it doesn't gate this review.)
- **S7** Run the rebuild + Xcode archive on the Mac (the rebuild itself is swarm-automatable; the archive/upload trigger is on the Mac).

### Automatable by the swarm (not a founder gate)
- **S7** `ns-ef-rebuild` compile/Capacitor-sync once real keys exist (S6).

### Passive / no work at all
- **7/21 web settlement** — `ch_3Tsv7qDK7Brrgheo1z3ksuF5` promotes PENDING → EARNING **automatically**. This is likely Epic Fury's **first retained dollar and it is entirely independent of this App Store path** — it needs nothing but a glance at the Stripe dashboard on/after 2026-07-21.

---

## Appendix — file citations used in this runbook
- `has_live_project_tracker/data/founder_handoff_queue.json` — all `ef-b*`, `rev-ef-*`, `apple-*` step contents + `rev-ef-iap-compliance-fix` = VERIFIED_IN_CODE.
- `docs/business/epic-fury-pricing-model.md` — 3.1.1 policy + product IDs `pro_monthly`/`pro_annual`.
- `docs/evidence/business/epic-fury-full-code-audit.md` — deps `@revenuecat/purchases-capacitor ^12.3.2` + `stripe ^22.0.2`; web-only Stripe routes; no live keys.
- `docs/evidence/business/epic-fury-onboarding-audit.md` — deps re-confirmed; no secret leaks.
- `docs/revenue/epic_fury_rebuild_verify.md` — build v3, dummy RevenueCat key baked, webhook secret SET, build dir path.
- `docs/founder/FOUNDER_EXECUTION_KIT_20260716.md` + `docs/journal/HELM_JOURNAL.md` — web charge `ch_3Tsv7qDK7Brrgheo1z3ksuF5` $20.52/$18.10, settles 2026-07-21.
- `docs/evidence/products/epic-fury-2026/security_scan_results_20260707.md` — Team ID K34GR8P326.
- **UNVERIFIED / not on disk:** `docs/revenue/epic_fury_pathB_resubmit_plan.md`, `docs/revenue/epic_fury_iap_compliance.md`, `docs/revenue/FIRST_DOLLAR_PLAN.md`, `docs/generated/r2/testflight_checklist.md`, `docs/generated/apple/*`, and the app-code files `lib/purchases.ts` / `PaywallModal` (live in the external `epic-fury-build` tree).
