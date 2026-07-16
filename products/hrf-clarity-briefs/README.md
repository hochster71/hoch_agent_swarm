# HRF — Clarity Briefs

**"The truth, in plain English, with receipts."**

Short, cited, jargon-free research briefs on the topics that shape real decisions —
health, money, policy, tech. Every claim links to a real source; every brief ends with
an explicit "what's still uncertain" section.

- **Price:** $5/mo subscription, or $2 per one-off brief.
- **Buyer:** curious non-experts, teachers, caregivers, small-business owners, journalists.
- **Registry:** `coordination/products/product_registry.json` → `HRF_CLARITY_BRIEFS` (spec: `docs/products/HCF_HRF_PRODUCT_SPECS.md`).

## Guardrail (honored)

Briefs **summarize and cite existing public sources** with a citation-per-claim rule and a
mandatory uncertainty section — clarity with receipts, not hot takes. They are information,
**not professional (medical/legal/financial) advice**. This disclaimer is shown on the landing
page and must appear on every generated brief. Same honesty doctrine as HELM: label what you
don't know; no false confidence.

## What is REAL vs STUB (NO FAKE GREEN)

**REAL (works as written):**
- Deployable static landing page (`public/index.html`) — name, what it is, both prices, working Buy buttons.
- `POST /api/create-checkout-session` — reads `STRIPE_SECRET_KEY` + `STRIPE_PRICE_MONTHLY`/`STRIPE_PRICE_BRIEF`
  from env and returns `{ "url": ... }`, mirroring the proven Story Studio checkout shape.
  Fails safe with a 501 when keys are absent (INERT until the founder sets keys).
- `vercel.json`, `.env.example` (placeholders only), success page.

**STUB / NOT BUILT (must not be claimed as done):**
- **The brief generator itself is not in this folder.** There is no automated pipeline here that
  reads sources and emits a cited brief. HRF has already produced 500+ synthesis/comparison artifacts
  (the underlying research muscle), but wiring that pipeline into a per-order brief generator with the
  enforced citation-per-claim + uncertainty rules is **remaining work**, not delivered here.
- No webhook / entitlement / delivery mechanism (how a paid subscriber actually receives their weekly
  brief) — out of scope for this MVP scaffold.

## Remaining work to make it genuinely sellable

1. Build the brief-generation pipeline (reuse HRF's existing research/synthesis skills) with a hard
   citation-per-claim linter + mandatory uncertainty section.
2. Add a delivery mechanism (email/reader) and a `/api/webhook` → entitlement store (mirror Story Studio's).
3. Founder-gated: create the two Stripe Prices ($5/mo, $2 one-off), set env vars, deploy to Vercel.
4. Pick one concrete launch vertical (e.g. "everyday health claims, decoded") so the buyer is concrete.

## Local shape

```
products/hrf-clarity-briefs/
  public/index.html          landing page + Buy buttons
  public/success.html        post-checkout thank-you
  api/create-checkout-session.js   POST -> { url }
  vercel.json
  .env.example
  package.json
```

Do **not** run `vercel deploy --prod` from here without the guard-railed pipeline. No keys are set;
no Stripe objects are created by this repo.
