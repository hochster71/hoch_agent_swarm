# Story Studio (HSF) — Go-Live Runbook

**Audience:** the founder (michael.b.hoch@gmail.com). YOU run every step below.
An agent cannot: log into Stripe/Vercel, create keys, deploy, or make a
purchase. This runbook exists so the ONLY things left are your irreducible
credential/deploy/purchase clicks.

**Status when this was written (2026-07-16):**
- Buy-loop code is complete and passes **10/10** mocked tests
  (`cd hsf/deploy && node --test`). Tests are logic-level (Stripe mocked,
  in-memory store) — NOT a live run.
- Deploy bundle lives in `hsf/deploy/` (checkout, signed webhook, entitlement
  store, KV-backed, fails-safe/INERT until real keys are set).
- Spec: `docs/factories/products/HSF_story_studio_checkout_spec.md`
- Impl evidence: `docs/evidence/runtime/hsf_buyloop_impl_20260716T135932Z.md`
- Env template: `hsf/deploy/.env.template`
- Preflight: `hsf/deploy/preflight_check.mjs`

**Guardrails baked into the code (so a half-config can't silently break):**
- No `STRIPE_SECRET_KEY` -> checkout & webhook return `501 not_configured`
  (`api/create-checkout-session.js` L36, `api/webhook.js` L53).
- No price ID -> checkout returns `501 price_not_configured` (L89).
- Bad/absent webhook signature -> `400 invalid_signature` (`api/webhook.js` L75).
- No Vercel KV -> `lib/store.js` falls back to an **in-memory Map wiped on cold
  start** (L50) — durable KV is required for real go-live (see step c4).

> UNVERIFIED assertion to confirm FIRST: repo tracker/spec docs claim the live
> Stripe account is `acct_1Tdge9DINF9KNAIC` with prices
> `price_1TqjVNDINF9KNAICvsZ4Kl3t` ($19 onestory) and
> `price_1TqjVNDINF9KNAICsqE8sy0G` ($12/mo creators). Those strings exist only in
> repo JSON — they are **NOT verified against your live Stripe dashboard**.
> Step (a) is where you confirm they really exist (or create them).

---

## Ordered steps

### (a) Stripe — confirm/create the two products & copy the live secret key

1. Go to **https://dashboard.stripe.com/** and toggle **View test data OFF**
   (top-right) so you are in **LIVE** mode.
2. Confirm the account: **Settings > Business** — verify the account id matches
   `acct_1Tdge9DINF9KNAIC` (asserted, UNVERIFIED). If it does not, you are in
   the wrong account — switch accounts before continuing.
3. Product catalog: **https://dashboard.stripe.com/products**
   - Find or **create** a **$19.00 USD one-time** product ("One-Story Export").
   - Find or **create** a **$12.00 USD / month recurring** product
     ("Creators Subscription").
4. For each price, open it and copy its **API ID** (looks like `price_...`).
   - Verify the $19 one-time price ID. Asserted: `price_1TqjVNDINF9KNAICvsZ4Kl3t`.
   - Verify the $12/mo price ID. Asserted: `price_1TqjVNDINF9KNAICsqE8sy0G`.
   - **If the asserted IDs are not present, use whatever the dashboard shows.**
     The code reads whatever you put in env — it assumes no specific IDs.
5. Copy the **live secret key**: **Developers > API keys > Secret key**
   (`sk_live_...`). **https://dashboard.stripe.com/apikeys**
   - **Acceptance check:** you now have 3 values written down privately:
     `sk_live_...`, the $19 `price_...`, the $12/mo `price_...`.
   - The prices should read exactly **$19.00 one-time** and **$12.00/month** in
     the dashboard. If they don't, fix the price before going live.

### (b) Generate AUTH_SECRET (reserved — ready-for-later, does not block $19 loop)

1. In a terminal run:
   ```
   openssl rand -base64 32
   ```
2. Save the output as `AUTH_SECRET`.
   - **Acceptance check:** you have a 44-char random string.
   - NOTE: no live code reads `AUTH_SECRET` yet — magic-link sign-in is a `501`
     stub (`api/auth/request-link.js`). Setting it now just means Creators
     self-serve login is ready when that ships. The $19 onestory buy loop does
     NOT depend on it.

### (c) Vercel — create/link project, add KV, set env vars, deploy `hsf/deploy/`

1. Install/login the CLI (once):
   ```
   npm i -g vercel
   vercel login
   ```
2. From the repo, link the deploy bundle:
   ```
   cd hsf/deploy
   vercel link
   ```
   Choose or create a project (e.g. `hsf-story-studio`). `vercel.json` already
   defines the function routes (checkout, webhook, entitlement, etc.).
3. **Set env vars.** Use `hsf/deploy/.env.template` as the checklist of NAMES.
   Either paste them in the dashboard
   (**Project > Settings > Environment Variables**, scope = Production) or via CLI:
   ```
   vercel env add STRIPE_SECRET_KEY production
   vercel env add STRIPE_PRICE_ONESTORY production
   vercel env add STRIPE_PRICE_CREATORS production
   vercel env add BASE_URL production
   # (STRIPE_WEBHOOK_SECRET is added in step d, after the endpoint exists)
   # (AUTH_SECRET optional, add it now if you like)
   ```
4. **Add Vercel KV (required for durable entitlements).**
   **Project > Storage > Create Database > KV**, then **Connect** it to this
   project. Vercel auto-injects `KV_REST_API_URL` and `KV_REST_API_TOKEN` —
   the two vars `lib/store.js` (L32) checks. Without both, entitlements live in
   an in-memory Map that is wiped on every cold start.
5. **First deploy:**
   ```
   vercel --prod
   ```
   - **Acceptance check:** deploy succeeds and prints a URL. Set `BASE_URL` to
     that URL (or your custom domain) if you didn't already, so Stripe redirects
     resolve. Hitting `https://<your-url>/api/entitlement?storyId=nope` should
     return `{"paid":false,...}` (proves the function is live and fails-open).

### (d) Register the live Stripe webhook, copy the signing secret, redeploy

1. **https://dashboard.stripe.com/webhooks** (LIVE mode) > **Add endpoint**.
2. Endpoint URL: `https://<your-deployed-url>/api/webhook`
   (route is defined in `vercel.json` L23-25 and served by `api/webhook.js`).
3. Select events to send (minimum for this code path — see `api/webhook.js`
   L85-139):
   - `checkout.session.completed`
   - `customer.subscription.deleted`
   - `customer.subscription.updated`
4. Save, then open the endpoint and copy its **Signing secret** (`whsec_...`).
5. Set it in Vercel and REDEPLOY so the webhook can verify signatures:
   ```
   vercel env add STRIPE_WEBHOOK_SECRET production
   vercel --prod
   ```
   - **Acceptance check:** in Stripe, **Send test webhook** for
     `checkout.session.completed`. The endpoint should respond **200** (a
     `501` means the secret isn't set; a `400 invalid_signature` from Stripe's
     own test means the wrong secret is set).

### (e) Run the preflight check

1. Pull the production env locally and validate (no network, no charge):
   ```
   cd hsf/deploy
   vercel env pull .env.production.local
   node --env-file=.env.production.local preflight_check.mjs
   ```
   (Or export the vars in your shell and run `node preflight_check.mjs`.)
   - **Acceptance check:** exit code `0` and "Preflight PASSED". If it exits `1`,
     fix every `[FAIL]` line (each names the var and where to get it) and rerun.
   - Reminder: preflight only checks shape/placeholders. It does NOT contact
     Stripe — step (f) is what proves the live path.

### (f) ONE real $19 test purchase -> confirm entitlement -> refund

> This is the single real-money step. Do it once, then refund immediately.

1. Open the storefront and start a real **$19 onestory** checkout. Note the
   `storyId` used (the client sends it; it becomes Stripe's
   `client_reference_id`). Complete payment with a **real card**.
2. Stripe fires `checkout.session.completed` -> your `/api/webhook` verifies the
   signature and writes `story:<storyId>` as paid (`api/webhook.js` L114-115).
3. Confirm the unlock:
   ```
   curl "https://<your-deployed-url>/api/entitlement?storyId=<storyId>"
   ```
   - **Acceptance check:** returns `{"paid":true,"tier":"onestory","source":"story"}`.
     The export UI should now unlock for that story.
4. **Refund it:** Stripe Dashboard > **Payments** > the $19 charge > **Refund**
   (full). **https://dashboard.stripe.com/payments**
   - **Acceptance check:** payment shows **Refunded**. (Note: refunding does not
     auto-revoke the one-time `story:` entitlement — that's expected; the point
     of this step is to prove the live buy->unlock path, not to test revocation.)

### (g) "Earning confirmed" — only when a balance transaction settles

- A `succeeded` charge is NOT the same as money in your account. Confirm at
  **https://dashboard.stripe.com/balance** that the $19 produced a **balance
  transaction** (it moves from *Pending* to your available balance per your
  payout schedule).
- **Acceptance check / definition of done:** a settled balance transaction for
  the real purchase (before you refunded, or on a second un-refunded real sale).
  Until a balance txn settles, treat "earning" as UNVERIFIED.

---

## The irreducible founder clicks (everything else is done)

1. Stripe: confirm/create $19 + $12/mo prices; copy `sk_live_...`. (step a)
2. `openssl rand -base64 32` -> `AUTH_SECRET`. (step b)
3. Vercel: link project, add KV, set env vars, `vercel --prod`. (step c)
4. Stripe: add `/api/webhook` endpoint, copy `whsec_...`, set it, redeploy. (step d)
5. `node --env-file=... preflight_check.mjs` -> exit 0. (step e)
6. One real $19 purchase -> `curl /api/entitlement` shows `paid:true` -> refund. (step f)
7. Confirm the balance transaction settled. (step g)

## Verification honesty
- 10/10 buy-loop tests pass **mocked/in-memory** — proves code coherence, NOT a
  live Stripe run.
- The Stripe account/price IDs above are **asserted in repo docs, UNVERIFIED on
  disk against the live dashboard** — step (a) is where you verify them.
- No agent has ever contacted Stripe/Vercel or moved money; all live actions
  above are yours.
