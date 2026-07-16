# HFF — Runway (Monthly Cash-Flow & Tax-Prep Packet)

An automated monthly packet for solo operators with no bookkeeper: a 30/60/90-day cash-flow
snapshot, a categorized transaction rollup, an estimated quarterly-tax worksheet, and a
year-end 1099-candidate list — assembled into one clean handoff for the user's own CPA.

- **Price:** $15/mo ($150/yr).
- **Buyer:** solo founders, freelancers, single-member LLCs who hand raw statements to a CPA.
- **Registry:** `coordination/products/product_registry.json` → `HFF_RUNWAY_PACKET` (spec: `docs/factories/products/HFF_runway.md`).

## Guardrail (honored)

**Organizational tooling ONLY — never financial, investment, or tax advice.** Every output must
carry a "prepared for your accountant; not advice" banner, mirroring the repo's existing tax-prep
skill doctrine. The landing page states this explicitly and the product files nothing on the user's
behalf. This is a hard, non-negotiable guardrail.

## What is REAL vs STUB (NO FAKE GREEN)

**REAL (works as written):**
- Deployable static landing page (`public/index.html`) — name, what it is, $15/mo price, working Buy button,
  and the "not advice" guardrail banner.
- `POST /api/create-checkout-session` — reads `STRIPE_SECRET_KEY` + `STRIPE_PRICE_MONTHLY` from env and
  returns `{ "url": ... }`, mirroring the proven Story Studio shape. Fails safe with 501 when keys are
  absent (INERT until the founder sets keys).
- `vercel.json`, `.env.example` (placeholders only), success page.

**STUB / NOT BUILT (must not be claimed as done):**
- **The packet generator itself is not in this folder.** There is no code here that ingests a bank CSV
  and emits the cash-flow snapshot / tax worksheet / 1099 list XLSX+PDF. The spec (`docs/factories/products/HFF_runway.md`)
  points at the repo's existing **tax-prep** and **cash-flow** skills as the intended engine — this MVP
  scaffold references them but does **not** wire them up or produce a real packet. No sample output is included
  here precisely to avoid faking functionality.
- No webhook / entitlement / file-delivery mechanism (how a paid subscriber uploads a CSV and gets a packet back).

## Remaining work to make it genuinely sellable

1. Build the packet generator: ingest a transactions CSV → categorized rollup + 30/60/90 cash-flow +
   estimated-quarterly-tax worksheet + 1099-candidate list, output as XLSX + one-page PDF. Reuse the
   existing tax-prep and cash-flow skills; add the advice-language linter (zero advice phrases) and
   math-reconciliation checks from the spec's acceptance criteria.
2. Add CSV upload + `/api/webhook` → entitlement store + packet delivery.
3. Founder-gated: create the $15/mo Stripe Price, set env vars, deploy to Vercel.

## Local shape

```
products/hff-runway/
  public/index.html          landing page + Buy button + not-advice banner
  public/success.html        post-checkout thank-you
  api/create-checkout-session.js   POST -> { url }
  vercel.json
  .env.example
  package.json
```

Do **not** run `vercel deploy --prod` from here without the guard-railed pipeline. No keys are set;
no Stripe objects are created by this repo.
