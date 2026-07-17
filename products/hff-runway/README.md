# HFF — Runway (Monthly Cash-Flow & Tax-Prep Packet)

An automated monthly packet for solo operators with no bookkeeper: a 30/60/90-day cash-flow
snapshot, a categorized transaction rollup, an estimated quarterly-tax worksheet, and a
year-end 1099-candidate list — assembled into one clean handoff for the user's own CPA.

- **Price:** $15/mo ($150/yr).
- **Buyer:** solo founders, freelancers, single-member LLCs who hand raw statements to a CPA.
- **Registry:** `coordination/products/product_registry.json` → `HFF_RUNWAY_PACKET`
  (spec: `docs/factories/products/HFF_runway_engine_spec.md`).

## Guardrail (honored, enforced in code)

**Organizational tooling ONLY — never financial, investment, or tax advice.** The engine
computes, categorizes, and shows math with every input labeled; it never tells the user what
to do. Every rendered artifact carries the banner **"Prepared for your accountant. Not
financial or tax advice."** An **advice-language linter** (`engine/advice_linter.js`) scans
every rendered string on every run and **fails the packet closed** if any advice phrase is
detected. This is a hard, non-negotiable guardrail and it is proven by a test that shows the
linter throwing on advice language.

## What is REAL vs STUB (NO FAKE GREEN)

**REAL — built and TESTED (34/34 assertions pass, `npm test`):**
- **The packet engine** (`engine/`): a deterministic pipeline that ingests a bank/transaction
  CSV and produces:
  - **Ingest & normalize** (`ingest.js`) — dependency-free CSV parser; auto-detects columns
    (date / description / amount, OR debit+credit); handles ISO, US, and `DD-Mon-YYYY` dates,
    `$`/comma/`(parentheses)` amounts, multiple shapes. Unparseable rows are **flagged with a
    reason, never silently dropped.**
  - **Categorize** (`categorize.js`) — deterministic keyword→category rules, user-overridable,
    fully auditable (each row records which rule fired). Produces the categorized rollup.
  - **Cash-flow** (`cashflow.js`) — 30/60/90-day inflow/outflow/net snapshot + average monthly
    burn + runway-in-months (needs `cash_on_hand`; labels "net-positive" when not burning).
  - **Estimated-tax worksheet** (`tax.js`) — SE tax (92.35% factor, 12.4% SS capped at the 2024
    wage base, 2.9% Medicare), ½-SE deduction, standard deduction, progressive federal brackets,
    total annual estimate, quarterly payment. **Every input is a labeled line** framed for the
    user's accountant. Uses published 2024 IRS figures as arithmetic inputs.
  - **1099-candidate list** (`tax.js`) — contractors grouped by payee, total paid, **>$600 rule**,
    missing-W-9 flag.
  - **Render & validate** (`render_xlsx.js`, `render_pdf.js`, `validate.js`) — emits a real
    multi-tab **`runway_packet_<UTC>.xlsx`** (Summary, Transactions, Categories, CashFlow,
    EstimatedTax, 1099 — verified to open as Excel 2007+) and a real **one-page `.pdf`** summary
    (dependency-free PDF writer, verified valid PDF 1.4). Non-advice banner on every sheet + the PDF.
- **Validation suite** (`validate.js`, run before every release): totals reconcile to the CSV;
  category percentages within [0,100] and sum to ~100; est-tax arithmetic independently
  recomputed and compared; quarterly×4 reconciles to annual; 1099 list matches the >$600 rule;
  runway is sane; disclaimer present. The engine **withholds the packet** if any check fails.
- **Sample inputs** (`engine/sample/`): three differently-shaped CSVs (signed-amount,
  debit/credit columns, categorized + parentheses/`DD-Mon` + a deliberately bad row). The engine
  runs on all three with no manual fixups.
- **Entitlement-gated API** (`api/generate-packet.js`): `POST { csv, profile, session_id }`.
  Gates on a **paid Stripe Checkout Session** when `STRIPE_SECRET_KEY` is set; INERT (501)
  otherwise unless `RUNWAY_DEV_UNLOCK=1` (local testing only). Returns the XLSX + PDF as base64.
  Mirrors the checkout's fail-safe shape. **No real payment logic and no money movement here.**
- Deployable static landing page, `POST /api/create-checkout-session` (fails safe 501 without
  keys), `vercel.json`, `.env.example`, success page — unchanged from the scaffold.

**STUB / NOT BUILT (must not be claimed as done):**
- **No CSV-upload UI.** The landing page has a Buy button but no file-upload form that calls
  `/api/generate-packet` and downloads the result. A subscriber currently can't self-serve
  through the browser — the engine is reachable only via the API (or `node`).
- **No Stripe webhook / persistent entitlement store.** Entitlement is checked live against the
  Stripe session id passed by the caller; there is no subscription-state database, no
  cancel/renew handling, no delivery email.
- **No live bank connection** (by design for v1 — user supplies the export).
- **Tax figures are 2024 constants.** They are labeled organizational inputs for the user's CPA,
  not filing-ready and not year-adaptive.

## Run it locally

```bash
cd products/hff-runway
npm install          # pulls exceljs (+ stripe)
npm test             # runs the engine on 3 sample CSVs -> 34/34 assertions
```

Entry function: `require('./engine').generateRunwayPacket({ csv, profile, generatedAt })`
returns `{ packet, validation, files: { xlsx, pdf, xlsxName, pdfName } }`.
`profile` accepts `{ filing_type, state?, as_of?, cash_on_hand?, w9_on_file?, category_overrides? }`.

## Remaining work to make it genuinely sellable

1. **Browser upload loop** — add a CSV-upload form to `public/` that POSTs to
   `/api/generate-packet` (with the paid `session_id`) and downloads the returned XLSX/PDF.
2. **Webhook + entitlement store** — add `/api/webhook` to record paid subscriptions and gate
   packet generation on stored entitlement (not just a passed session id), plus renewal/cancel.
3. **Founder go-live (gated, NOT done here — Michael's clicks):**
   - Create the $15/mo Stripe Price → set `STRIPE_SECRET_KEY` + `STRIPE_PRICE_MONTHLY` in Vercel.
   - Deploy via the guard-railed pipeline **only** (`scripts/factory_deploy.sh`) — never
     `vercel deploy --prod` from here.
   - Smoke-test the buy → upload → packet loop end-to-end in Stripe test mode before `sk_live_`.

## Local shape

```
products/hff-runway/
  engine/
    index.js            entry: generateRunwayPacket()
    ingest.js           CSV parse + column auto-detect + reject-flagging
    categorize.js       deterministic keyword rules + rollup
    cashflow.js         30/60/90 snapshot + runway
    tax.js              estimated-tax worksheet + 1099 list
    validate.js         pre-release validation suite
    advice_linter.js    banned-phrase gate (fails closed)
    render_xlsx.js      multi-tab workbook (exceljs)
    render_pdf.js       dependency-free one-page PDF
    constants.js        tax params, category rules, disclaimer
    sample/             3 differently-shaped sample CSVs
  test/engine.test.js   34-assertion validation suite
  api/
    create-checkout-session.js   POST -> { url }   (scaffold, unchanged)
    generate-packet.js           POST -> packet    (entitlement-gated)
  public/, vercel.json, .env.example, package.json
```

Do **not** run `vercel deploy --prod` from here without the guard-railed pipeline. No keys are
set; no Stripe objects are created by this repo; no money is moved by this code.
