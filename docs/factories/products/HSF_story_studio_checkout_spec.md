# HSF — Story Studio Checkout Build Spec (path to SELLABLE, then first EARNING dollar)

**Factory:** HSF (mission_control label "Hoch Storybook Factory · Story Studio"; census `FACTORY_INTENT` label "Hoch Story Factory")
**Product:** `HSF_STORY_STUDIO` — Story Studio One-Story Export ($19 one-time) + Creators ($12/mo)
**Authored (UTC):** 2026-07-16 · read-only discovery pass, no runtime state touched.
**Doctrine:** NO FAKE GREEN. Every claim is bound to a file. EXISTS-today vs MISSING vs FOUNDER-GATED are labeled. Monetization ≠ revenue: a product is SELLABLE only when a stranger can reach a real checkout, and EARNING only when a real charge **settles**. Do not dispatch any step below until the active Phase C soak seals.

---

## 1. What EXISTS today (evidence-cited, on disk)

| Piece | File | State |
|---|---|---|
| Story Studio app UI | `hsf/story-studio-v2.html` | EXISTS. Free in-browser builder; `checkout('onestory')` / `checkout('creators')` buttons POST to `/api/create-checkout-session`. Also calls `/api/story-brief`, `/api/auth/request-link`, `/api/export`, `/api/art`, `/api/entitlement`. |
| Story engine | `hsf/story-engine.js` | EXISTS. |
| Checkout session creator | `hsf/deploy/api/create-checkout-session.js` | EXISTS. Env-driven, **INERT**: returns `501 not_configured` with no `STRIPE_SECRET_KEY`. Resolves/creates a Stripe Payment Link for the price, else falls back to a Checkout Session. |
| Stripe webhook handler | `hsf/deploy/api/webhook.js` | EXISTS. Verifies signature; on `checkout.session.completed` grants entitlement; handles `customer.subscription.deleted/updated`. **`require('../lib/store')` — that file does NOT exist**, so the handler crashes at runtime today. |
| Pricing config | `hsf/deploy/pricing.config.json` | EXISTS. `onestory` $19 one_time, `creators` $12/month; price IDs read from env, none baked. |
| Vercel config | `hsf/deploy/vercel.json` | EXISTS. Routes `/api/{create-checkout-session,save-story,download,webhook,entitlement,auth/request-link,auth/verify,export,share,morph}` — most target files that **do not exist yet**. |
| Env template / README | `hsf/deploy/.env.example`, `hsf/deploy/README.md` | EXISTS. All placeholder values (`sk_test_REPLACE_ME`, `price_REPLACE_ME_*`). README declares the scaffold FOUNDER-gated and inert until keys added. |

## 2. What is MISSING (blocks the buy loop end-to-end)

- `hsf/deploy/lib/store.js` — the Vercel KV wrapper (`setPaid/setUnpaid/put/get`) that `webhook.js` and any `entitlement` route import. **Absent — webhook will throw `MODULE_NOT_FOUND` on the first paid event.**
- API routes referenced by `vercel.json` and/or the HTML but not on disk: `api/save-story.js`, `api/download.js`, `api/entitlement.js`, `api/auth/request-link.js`, `api/auth/verify.js`, `api/export.js`, `api/share.js`, `api/morph.js`, `api/story-brief.js`, `api/art.js`.
- `hsf/deploy/package.json` — no manifest; `stripe` dependency not declared (README tells the founder to `npm init` + `npm install stripe`).
- Storefront entry the queue names as `public/index.html` — not present under `hsf/deploy/`; the actual UI lives at `hsf/story-studio-v2.html` and is not yet placed as the deploy site root.
- No `.env` / no keys anywhere (correct and safe, but means zero live wiring).

## 3. Stripe "LIVE" claim — UNVERIFIED (honest flag)

`has_live_project_tracker/data/founder_handoff_queue.json` item `ss-stripe-account-bootstrap` is marked **DONE** with `result`: LIVE account `acct_1Tdge9DINF9KNAIC`, `onestory price_1TqjVNDINF9KNAICvsZ4Kl3t` ($19), `creators price_1TqjVNDINF9KNAICsqE8sy0G` ($12/mo). The FIRST_DOLLAR packet repeats this.

**Corroboration on disk: none.** Those account/price identifiers appear only in the queue JSON and the packet that quotes it — not in any code or config. Every setup doc the queue cites (`docs/revenue/stripe_setup_steps.md`, `story_studio_go_live.md`, `STORY_STUDIO_GO_LIVE_NOW.md`, `story_studio_stripe_spec.md`, `bootstrap-stripe.js`) **does not exist**; `docs/revenue/` holds only `epic_fury_rebuild_verify.md`. Treat "Stripe is live for Story Studio" as an **asserted-but-unverified** queue claim. It must be re-confirmed against the real Stripe account (founder or authorized live read) before relying on it. No live checkout URL exists.

---

## 4. Path to SELLABLE — (a) AGENT-BUILDABLE steps (run only AFTER the soak seals)

These touch only repo files under `hsf/deploy/`; none spend money, deploy, or need a live key.

- **A1. Write `hsf/deploy/lib/store.js`** — KV wrapper exposing `setPaid/setUnpaid/put/get`, backed by Vercel KV (`@vercel/kv`) with a no-op-and-log fallback when KV env is absent (mirrors the comment already in `webhook.js`). Unblocks the webhook.
- **A2. Add `hsf/deploy/api/entitlement.js`** — reads `story:<id>` / `email:<addr>` from the store so the UI's `/api/entitlement` check returns paid/unpaid. Gate export/download on it.
- **A3. Build the remaining referenced routes** that the product needs for the minimal paid loop: `api/save-story.js`, `api/download.js`, `api/export.js` (and stub/return-501 the non-essential `share`, `morph`, `story-brief`, `art`, `auth/*` so `vercel.json` has no dangling routes). Keep every one FAIL-SAFE (501 when unconfigured), matching the existing scaffold style.
- **A4. Add `hsf/deploy/package.json`** declaring `stripe` (and `@vercel/kv`) as dependencies, CommonJS (no `"type":"module"`).
- **A5. Place the deploy site root** — copy/adapt `hsf/story-studio-v2.html` to the deploy `public/index.html` (or set Vercel output dir) so the storefront is served.
- **A6. Local test harness** — a script (Stripe test keys, `stripe listen --forward-to`) that drives `create-checkout-session` → simulated `checkout.session.completed` → asserts `store.js` records the entitlement and `/api/entitlement` flips to paid. **Test-mode only; no live key, no real charge.** Produces a pass/fail artifact under `docs/evidence/`.

**Exit of section (a):** a coherent, test-passing, still-inert deploy bundle. Not yet sellable (no live keys / not deployed).

## 5. Path to SELLABLE — (b) FOUNDER-ONLY steps (irreducible money/credential/deploy acts)

Maps to queue items `ss-stripe-live` + `hsf-story-studio-go-live` (status SIGNED, **execution pending**).

- **F1. Confirm / provision the live Stripe catalog** — verify `acct_1Tdge9DINF9KNAIC` and the two price IDs actually exist and are live in the Stripe dashboard (the disk cannot prove this). Re-create if the claim doesn't hold.
- **F2. Provision Vercel KV** for the store.
- **F3. Set live env in Vercel** — `STRIPE_SECRET_KEY` (`sk_live_…`), `STRIPE_PRICE_ONESTORY`, `STRIPE_PRICE_CREATORS`, `AUTH_SECRET`, `BASE_URL`, plus KV vars. Secrets provisioned directly, never in chat.
- **F4. Deploy** to Vercel production (`vercel deploy --prod`).
- **F5. Register the LIVE webhook** at `https://<deployment>/api/webhook` (subscribe `checkout.session.completed`, `customer.subscription.deleted`, `customer.subscription.updated`), capture `whsec_…` into `STRIPE_WEBHOOK_SECRET`, redeploy.
- **F6. First-dollar proof purchase** — make ONE real $19 `onestory` purchase, confirm the export unlocks, then refund (net-zero self-test). Then capture the live checkout/Payment-Link URL and write it into `checkout_url` in the registry.

Once F4+F5 land and the checkout URL is reachable by a stranger, the product is **SELLABLE** (rung 4). It is still not EARNING until a real charge settles.

---

## 6. Acceptance criteria — FIRST-DOLLAR proof (rung 5 EARNING)

Monetization ≠ revenue. Promote `HSF_STORY_STUDIO` to `5_EARNING` **only** when ALL hold, each verified against the Stripe account (not asserted):

1. A real livemode `charge` (`ch_…`) exists for the $19 `onestory` price on the Story Studio account. Record `stripe_charge_id`, `first_charge_at`.
2. The signed webhook fired and `lib/store.js` recorded the matching entitlement (a real settled ledger row: `story:<id>` or `email:<addr>` marked paid, tied to the charge's `sessionId`).
3. The balance transaction has **settled** (`revenue_settled_usd > 0`, `revenue_state: EARNING`) — not merely `PENDING_SETTLEMENT`. Until then the row stays `PENDING_SETTLEMENT`, exactly as `EPIC_FURY_2026` models it.
4. `checkout_url` in `coordination/products/product_registry.json` is a real URL a stranger can open, and `checkout_blocked_by` is `null`.

A self-test purchase that is refunded proves the *loop*, not retained revenue; the first **retained** dollar is the first real stranger customer after the storefront URL is shared.

## 7. Doctrine reminder

Defined ≠ produced ≠ sellable ≠ earning. Today Story Studio sits at **3_PRODUCTIZED_DEFINED_ONLY**: real app + inert scaffold, an *unverified* Stripe-live claim, no reachable checkout, missing store lib, $0 settled. Do not paint it green. No fake checkout_url, no invented charge. All of section 5 is FOUNDER-GATED; all of section 4 waits until the soak seals.
