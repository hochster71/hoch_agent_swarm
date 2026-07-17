# HFF — Invoice Aging Snapshot

Upload an accounts-receivable / invoice CSV → get a clean **30/60/90 aging report** and a
**who-owes-what** summary as an **XLSX workbook** and a **one-page PDF**. Built for freelancers
and small shops chasing unpaid invoices without accounting software.

**Price:** $9, one-time. **Merchant of record:** Stripe managed payments.

> **Guardrail — organizational tooling only.** This product organizes your own numbers to show
> which invoices are outstanding and how old they are. It is **not** financial, collections, or
> legal advice, and it never contacts anyone or collects anything for you. The engine hard-fails
> (fail-closed) if any advice language would appear in an artifact.

---

## What's REAL vs STUB

**REAL (works today, verified by tests):**
- **Aging engine** (`engine/`) — deterministic CSV → aging pipeline: ingest → bucket by days-past-due
  → roll up by customer → validate → render. Handles multiple CSV shapes (amount+paid, balance
  column, status column), currency symbols (`$ £ €`), parenthesized negatives, and multiple date
  formats (`YYYY-MM-DD`, `M/D/YYYY`, `DD-Mon-YYYY`). Unparseable rows are **flagged**, never dropped.
- **XLSX workbook** (`exceljs`) — Summary, Buckets, ByCustomer, Aging (per-invoice) tabs, non-advice
  banner on every sheet.
- **One-page PDF** — dependency-free, valid PDF 1.4.
- **Advice linter** — scans every rendered string; refuses to release the report if banned
  financial/collections/legal-advice language appears (fail-closed).
- **Validation gate** — bucket totals, customer totals, counts, and percentages must reconcile or
  the report is withheld.
- **Checkout → webhook → entitlement loop** (`api/`, `lib/store.js`) — signature-verified Stripe
  webhook grants a per-session entitlement; the generator gates on it. **Inert (HTTP 501) until keys
  are set.** Store uses Vercel KV when configured, in-memory fallback otherwise.
- **Landing + delivery UI** (`public/`) — `index.html` (buy), `success.html`, `app.html`
  (upload/paste CSV → download XLSX/PDF).

**STUB / NOT DONE (founder gate — intentionally not crossed by the factory):**
- **No live Stripe account, price, keys, or deploy.** All Stripe values are read from env vars and
  are placeholders in `.env.example`. Nothing is wired to a real account.
- **Buy-loop tests are MOCKED** — `test/buyloop.test.js` mocks the `stripe` package and runs the
  entitlement store in-memory. It proves the code paths are coherent; it is **not** a live Stripe
  test-mode run.
- **No durable store in production until Vercel KV is provisioned** (falls back to in-memory, which
  is per-invocation and not durable on serverless).

---

## Tests (real results)

```
npm install
npm test
```

Last local run (`node v22`): **engine suite 48/48 passed**, **buy-loop 10/10 passed**. The advice
linter is proven to fail-closed on advice language, and the webhook is proven to reject a bad
signature (400) and to be inert without keys (501).

---

## Founder go-live steps (the only thing left)

Everything above is built to the doorstep. To take it live, the founder:

1. **Create the Stripe price** in your live account: a **$9 one-time** price. Note its `price_...` id.
2. **Set env vars** in Vercel (Project → Settings → Environment Variables):
   - `STRIPE_SECRET_KEY` = `sk_live_...`
   - `STRIPE_PRICE_REPORT` = the `price_...` from step 1
   - `STRIPE_WEBHOOK_SECRET` = `whsec_...` (from the Stripe webhook endpoint you create for
     `POST /api/webhook`, subscribed to `checkout.session.completed`)
   - `BASE_URL` = your deployed URL
   - *(recommended for durable entitlements)* `KV_REST_API_URL` + `KV_REST_API_TOKEN` from a
     provisioned Vercel KV store.
3. **Deploy via the guard-railed pipeline** — `scripts/factory_deploy.sh` (source-match guard →
   preview → smoke-test → promote → auto-rollback). Do **not** `vercel --prod` from an unverified
   folder.

Until step 2 is done, checkout and generation return **501 not_configured** and no money can move.

---

## Layout

```
engine/            deterministic aging pipeline (no network, no secrets)
  constants.js       disclaimer, aging buckets, thresholds
  ingest.js          CSV parse + column detection + balance derivation
  aging.js           days-past-due + bucketing
  summary.js         who-owes-what rollup by customer
  validate.js        fail-closed reconciliation checks
  advice_linter.js   fail-closed advice-language guard
  render_xlsx.js     exceljs workbook
  render_pdf.js      dependency-free one-page PDF
  index.js           entry point: generateAgingReport()
  sample/            three sample CSVs used by the tests
api/               Vercel serverless endpoints (inert without keys)
  create-checkout-session.js
  webhook.js         signature-verified, fail-closed
  entitlement.js
  generate-report.js entitlement-gated delivery
lib/store.js       KV-or-in-memory entitlement store
public/            landing + delivery UI
test/              engine.test.js (48) + buyloop.test.js (10, mocked)
```
