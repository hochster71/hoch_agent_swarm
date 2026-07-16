# Founder Action Pack — 2026-07-15 (evening)

Everything here is **yours to do** (money / keys / deploy / publish / product judgment). None of it
touches the running soak, and the 8-factory moonshot auto-fires tomorrow ~3:30 PM CDT after the seal.
Work these in the order that suits you — but items 1–3 directly unblock real revenue.

---

## 1. Ship the tactical icon to the App Store  ⏱️ ~20 min

**Evidence:** Live App Store version **1.0 is on build 8** (confirmed via App Store Connect API just now).
Build 8 predates the icon — so the live app shows the **placeholder**, not the tactical radar icon.
The icon is already installed in the Xcode project (`~/epic-fury-build/epic-fury-2026`, verified 1024×1024,
no alpha, backup kept).

**To ship it:**
1. Open `~/epic-fury-build/epic-fury-2026/ios/App/App.xcworkspace` in Xcode → Assets → AppIcon.
   Confirm the tactical radar icon shows (not the placeholder).
2. Bump the build number (build 8 → **10**; build 9 already exists in TestFlight — check whether *it*
   has the icon first, and if so you can just use 9).
3. Product → Archive → Distribute App → upload.
4. In App Store Connect: create a new version (**1.0.1**), attach the icon build, submit for review.

*Note: the live-app icon only updates with a new reviewed build — there's no faster path.*

---

## 2. Make the Stripe account payout-ready  ⏱️ ~30–45 min  ← highest leverage

This is the single unlock for **all 8 factories**. Every factory's rung 4→5 (the actual dollar) settles
through Stripe. If the account isn't payout-ready, everything the swarm builds still stalls at the finish.

Account: **Epic Fury** (`acct_1TPOYkDK7Brrgheo`). In the Stripe Dashboard, confirm:
- [ ] **Business details** verified (legal entity / name / address / EIN or SSN).
- [ ] **Bank account** linked for payouts, and payout schedule set.
- [ ] **Identity verification** complete (no "action required" banners).
- [ ] **Tax** — Stripe Tax enabled or your tax handling decided (you're merchant of record on web).
- [ ] Note the **first Epic Fury payout date** — your $20.52 charge (net $18.10) settles **July 21**;
      that becomes HELM's first genuinely *earned* dollar the moment it lands.

---

## 3. Set up Story Studio's Stripe products (HSF is closest to a 2nd product)  ⏱️ ~20 min

Story Studio's checkout scaffold is built and waiting; it just needs live products + keys. Pre-create
these tonight and tomorrow's HSF swarm output plugs straight in.

**Create two products in Stripe** (Products → Add product), currency USD:

| Product | Price | Type | Env var it fills |
|---|---|---|---|
| **One-Story Export** | **$19.00** | one-time | `STRIPE_PRICE_ONESTORY` |
| **Creators Subscription** | **$12.00 / month** | recurring | `STRIPE_PRICE_CREATORS` |

Then, in the **Vercel** project for Story Studio, set these env vars (do NOT commit them anywhere):
- [ ] `STRIPE_SECRET_KEY` — live secret key (`sk_live_…`)
- [ ] `STRIPE_WEBHOOK_SECRET` — from Stripe → Developers → Webhooks → add endpoint
      `https://<your-deploy>/api/webhook`, subscribe to `checkout.session.completed`
- [ ] `STRIPE_PRICE_ONESTORY` — the price ID from the One-Story product
- [ ] `STRIPE_PRICE_CREATORS` — the price ID from the Creators product
- [ ] `BASE_URL` — your deployed Story Studio URL

*The scaffold "fails safe": with no `STRIPE_SECRET_KEY` it stays inert, so nothing charges until you're ready.*

---

## 4. Decide what the 4 blank factories should *be*  ⏱️ ~15 min of judgment

HFF, HHF, HMF, HPF are empty config entries. Tomorrow's swarm will *propose* product candidates, but your
call on the lane is the highest-value input. For each, pick a direction (or write your own):

**HFF — Finance Factory** (financial tooling)
- (a) *Founder cash-runway dashboard* — subscription; small business owners. **[recommended: recurring revenue]**
- (b) One-time financial-model template pack (fundraising, unit economics).
- (c) A narrow calculator/API product.
- Your call: __________

**HHF — Home Factory** (home / personal automation)
- (a) *Home-automation blueprint pack* — one-time; smart-home owners.
- (b) Personal-ops companion (routines/checklists) — subscription.
- (c) Template/config marketplace.
- Your call: __________

**HMF — Music Factory** (music / audio — **original works only, no copyrighted material**)
- (a) *Royalty-free original music pack* — one-time; creators/streamers. **[recommended: clean IP, clear buyer]**
- (b) Generative background-music tool — subscription.
- (c) Custom jingle/stinger service.
- Your call: __________

**HPF — Pods Factory** ("physical/digital goods" — *this one needs your definition most*)
- ❓ **What is "Pods"?** — podcast production kit? digital product bundles? print-on-demand? something else?
- Tell me what you intend and I'll aim the swarm precisely. Your call: __________

---

## What's running for you while you sleep
- **24h soak** → seals tomorrow **~2:45 PM CDT** (last piece of "proven 24/7").
- **Seal check** → auto-runs **3:15 PM**, reports clean/failed.
- **8-Factory Moonshot** → auto-fires **3:30 PM** *if the soak sealed cleanly* — all 8 factories start
  climbing the revenue ladder in parallel, each stopping at a founder gate for anything that spends or ships.
- **Epic Fury's first dollar** settles **July 21**.

Reply with your item-4 choices anytime and I'll fold them into the moonshot missions so the swarm builds
toward real products, not guesses.
