# HASF Billing — Go-Live Checklist (Founder-Owned)

Billing ships **test-mode by default**. Nothing in this repo can charge a real
card until *you* complete the steps below. The agent will not throw the live
switch — that is a founder action by design.

## Current state (scaffolding complete)
- Stripe SDK vendored (`stripe>=15.3.0`).
- Keys in `.env` are **test-mode** (`sk_test_` / `pk_test_`).
- Endpoints live under `/api/stripe`:
  - `GET /api/stripe/catalog` — public pricing + mode banner
  - `GET /api/stripe/mode` — effective billing mode
  - `POST /api/stripe/checkout` — create a Checkout Session (test mode)
  - `POST /api/stripe/webhook` — signature-verified, idempotent, provisions entitlements
- Pricing catalog (`backend/billing/pricing_catalog.json`): Free · Pro monthly/annual · Team monthly · Lifetime (one-time).
- Fail-closed guard (`backend/billing/mode.py`): a live key with the switch OFF is **blocked** (`test_locked`).

## The three founder-chosen models
| Model | Tier(s) | Stripe checkout mode |
|---|---|---|
| Freemium | Free | none |
| Subscription | Pro (monthly/annual), Team (monthly) | `subscription` |
| One-time | Lifetime | `payment` |

## Step 1 — Create products & prices in Stripe **TEST** mode
In the Stripe Dashboard (test mode) or via API, create a Price for each paid tier.
Copy each test price id into `pricing_catalog.json` → `stripe.test_price_id`,
replacing the `REPLACE_*` placeholders.

## Step 2 — Smoke-test the full loop (test mode, no real money)
1. Start the API; `GET /api/stripe/mode` should report `effective_mode: test`.
2. `POST /api/stripe/checkout {"tier_id":"pro_monthly"}` → follow the returned `url`,
   pay with test card `4242 4242 4242 4242`.
3. Point a Stripe webhook (or `stripe listen`) at `/api/stripe/webhook`.
4. Confirm `data/billing/entitlements.json` shows the customer granted `pro / active`.

## Step 3 — Prove demand (contract gate G-1) BEFORE live
Per the unified goal contract, monetization must be validated by real demand
before go-live: ≥10–20 prospects, 3–5 discovery calls, ≥1 willingness-to-pay
signal, ≥1 named buyer. Log evidence via `scripts/verify_demand_validation.py`.

## Step 4 — Throw the live switch (founder only)
1. Create the **live** products/prices in Stripe; put their ids in
   `stripe.live_price_id` (kept out of source until now — set them at go-live).
2. Put live keys in `.env`: `STRIPE_SECRET_KEY=sk_live_...`,
   `STRIPE_PUBLISHABLE_KEY=pk_live_...`, `STRIPE_WEBHOOK_SECRET=whsec_...` (live endpoint).
3. Set `HASF_BILLING_LIVE=1`.
4. Verify `GET /api/stripe/mode` → `effective_mode: live`.
   Until **both** the live key and `HASF_BILLING_LIVE=1` are present, the guard
   stays in `test_locked` and refuses live charges.

## Safety invariants (enforced in code)
- No real charge without a live key **and** `HASF_BILLING_LIVE=1`.
- Webhook rejects unsigned/mis-signed payloads (HMAC over raw body).
- Duplicate events ignored (idempotency guard).
- `live_price_id` must be null in committed source (catalog validation fails otherwise).
