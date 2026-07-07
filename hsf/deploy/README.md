# Hoch Storybook Factory (HSF) — Deploy Scaffold

A **deploy-ready skeleton** for the HSF monetization layer: a static site plus
two Node serverless functions on Vercel, wired to Stripe for the
**free-preview → paid-export** model.

> **This scaffold is INERT by design.** With no keys set, every payment
> endpoint returns a clear `501 not configured` response. Nothing charges a
> card, nothing goes live, until the founder adds real keys. See
> **[Founder-gated actions](#founder-gated-actions-doorstep)** below.

---

## What's in here

| File | Purpose |
|------|---------|
| `vercel.json` | Vercel config: static site + Node serverless functions. |
| `api/create-checkout-session.js` | Creates a Stripe Checkout Session for a given `tier`. |
| `api/webhook.js` | Verifies Stripe signatures; logs entitlement grants on `checkout.session.completed`. |
| `pricing.config.json` | The two tiers (id, label, price, interval, price env var, features). |
| `.env.example` | Every env var needed, with comments. No real values. |
| `.gitignore` | Ignores `.env` and `node_modules`. |

### The two products

| Tier id | Label | Price | Type |
|---------|-------|-------|------|
| `onestory` | One-Story Export | **$19** | one-time payment |
| `creators` | Creators Subscription | **$12 / month** | recurring subscription |

---

## Founder-gated actions (DOORSTEP)

The following are **FOUNDER-ONLY** actions. The build agent does **not** perform
them, and this scaffold will not perform them automatically:

1. **Adding real Stripe keys** (test or live).
2. **Going live** (swapping test keys `sk_test_...` for live keys `sk_live_...`).
3. **Enabling payments** (registering the live webhook and taking real money).

The agent's job ends at "safe, inert scaffold." Turning it on is the founder's
call. Until the founder does step 1, the endpoints fail safe with `501`.

---

## Prerequisites (one-time)

- A [Stripe](https://dashboard.stripe.com) account.
- A [Vercel](https://vercel.com) account + the CLI: `npm i -g vercel`.
- The `stripe` npm package as a dependency. This folder ships without a
  `package.json`; create one before deploying:

  ```bash
  cd hsf/deploy
  npm init -y
  npm install stripe
  ```

  Then set **`"type": "commonjs"`** (or simply omit `"type"`) in that
  `package.json` — the functions here use CommonJS (`module.exports` /
  `require`). Do **not** set `"type": "module"` unless you convert the
  functions to ESM `import`/`export` first.

---

## Launch runbook

### (a) Create the two Stripe products / prices

1. In the Stripe dashboard, switch to **Test mode** first (toggle, top-right).
2. **Products → Add product**:
   - **One-Story Export** — pricing model **One time**, amount **$19.00**.
     Save, then copy the **Price ID** (`price_...`).
   - **Creators Subscription** — pricing model **Recurring**, **$12.00 / month**.
     Save, then copy its **Price ID** (`price_...`).
3. Keep both Price IDs handy for step (b).

### (b) Set env vars in Vercel

Set these in **Vercel → Project → Settings → Environment Variables**
(see `.env.example` for the full annotated list):

| Var | Value |
|-----|-------|
| `STRIPE_SECRET_KEY` | Your Stripe secret key (`sk_test_...` for now) |
| `STRIPE_WEBHOOK_SECRET` | From step (d) — set after registering the webhook |
| `STRIPE_PRICE_ONESTORY` | The `price_...` for One-Story Export |
| `STRIPE_PRICE_CREATORS` | The `price_...` for Creators Subscription |
| `BASE_URL` | Your deployed URL, e.g. `https://your-app.vercel.app` |

For **local** testing, copy `.env.example` to `.env` and fill it in locally
(`.env` is git-ignored — never commit it).

### (c) Deploy

```bash
cd hsf/deploy
vercel deploy          # preview deploy
# ...verify, then:
vercel deploy --prod   # production deploy
```

### (d) Configure the webhook endpoint

1. In Stripe: **Developers → Webhooks → Add endpoint**.
2. Endpoint URL: `https://<your-deployment>/api/webhook`.
3. Subscribe to at least: **`checkout.session.completed`** (and, for
   subscriptions, `customer.subscription.deleted`).
4. Copy the endpoint's **Signing secret** (`whsec_...`) into the
   `STRIPE_WEBHOOK_SECRET` env var in Vercel, then **redeploy** so it takes
   effect.

### (e) Test with Stripe test cards

With test keys set, POST to the checkout endpoint:

```bash
curl -X POST https://<your-deployment>/api/create-checkout-session \
  -H "Content-Type: application/json" \
  -d '{"tier":"onestory"}'
# -> { "url": "https://checkout.stripe.com/..." }
```

Open the returned `url` and pay with a Stripe **test card**:

- Success: `4242 4242 4242 4242`, any future expiry, any CVC, any ZIP.
- Declined: `4000 0000 0000 0002`.

Confirm the webhook fires — the Stripe dashboard shows delivery, and your
Vercel function logs print `ENTITLEMENT GRANT -> {...}`. You can also replay
events locally with the Stripe CLI: `stripe listen --forward-to localhost:3000/api/webhook`.

**Going live** (founder-gated): repeat (a)–(d) in Stripe **Live mode**, swap in
live keys, and only then accept real payments.

---

## Security notes

- **Never commit real keys.** `.env` is git-ignored. All secrets live in Vercel
  env vars (or your local, un-committed `.env`).
- **No secrets in code.** The functions only read `process.env.*`; there are no
  hardcoded keys anywhere in this scaffold.
- **Fails safe.** Missing `STRIPE_SECRET_KEY` (or a missing price/webhook
  secret) returns a clear `501` — it never runs with a broken/placeholder key.
- **Signature verification.** The webhook rejects any event that doesn't verify
  against `STRIPE_WEBHOOK_SECRET`, so forged calls can't grant entitlements.
- If a key is ever exposed, **roll it immediately** in the Stripe dashboard.
