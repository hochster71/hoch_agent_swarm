# HFF — Client Revenue Concentration Report

**Upload an invoice CSV → see exactly how your revenue is distributed across your clients.**
$9 one-time. No account, no bank connection, no stored file.

Status: **CODE-COMPLETE (doorstep).** Built and tested by the HELM autonomous factory loop.
**$0 earned. Nothing deployed. No Stripe price, no keys.** Only a founder deploy remains — see
[Founder go-live](#founder-go-live).

---

## What it does

Given a CSV of invoices (date, client, amount), it produces a deterministic report:

| Output | Detail |
|---|---|
| **Per-client breakdown** | Net revenue, share of total, invoice count, gross vs credits, average / largest / smallest invoice, first and last invoice, months with revenue, median days-to-pay |
| **Concentration figures** | Top 1 / 3 / 5 / 10 share, HHI on the standard 0–10,000 scale, effective client count (1 / Σ share²), and how few clients make up the first 50% and 80% |
| **Monthly series** | Net, gross, credits, active clients, and the largest client per calendar month |
| **Dormancy** | Clients whose gap since their last invoice exceeds **2× that client's own median gap** — measured per client, not against a fixed threshold |
| **Spelling merge** | "Acme Corp" / "ACME CORPORATION" / "Acme, Inc." collapse to one client; every merge is disclosed in the report so you can check it |
| **Flagged rows** | Every unreadable row with its CSV line number and reason. Nothing is silently dropped |

Delivered as a **5-sheet XLSX workbook** (Summary · Clients · Monthly Revenue · All Invoices ·
Flagged Rows) and a **one-page PDF summary**. Both are byte-deterministic for a given input.

A **free, ungated preview** runs the same engine and returns the top-line figures, so a stranger
can confirm the tool works before paying.

### Input format

Required columns: a **date**, a **client name**, an **amount**. Header names are aliased
generously (`Invoice Date` / `Issue Date` / `Posted Date`; `Client` / `Customer` / `Account` /
`Bill To`; `Amount` / `Total` / `Invoice Total` / `Revenue`). Optional: `Invoice Number`,
`Paid Date`, `Status` — a paid-date column unlocks the payment-timing figures.

Handles RFC4180 quoting, CRLF, BOM, `$`/`£`/`€`, thousands separators, EU decimal commas,
parenthesised negatives, trailing-minus, and ISO / US / UK dates with whole-file order detection.

---

## Guardrail

**Organizational tooling only. Not financial, tax, or legal advice.** The report describes how
revenue in the uploaded file is distributed. It never says a distribution is good or bad, and never
tells the reader which clients to keep, chase, drop, or re-price.

This is enforced by a **fail-closed advice linter** (`engine/advice_linter.js`) that runs *before
any artifact bytes are produced*. A violation withholds the entire report — paid or free — and
surfaces as HTTP 422. It never ships a degraded or partially-linted artifact.

**Linter design improvement over the sibling HFF products.** Notes that embed a client's name carry
a parallel *lint-safe* twin in which the name is replaced by `<client>`. The linter runs against
those twins. This means the engine's own wording stays fully guarded, **and** a buyer whose client
is genuinely called "Good Client LLC" or "We Recommend Ltd" does not have their paid report
withheld by a false positive on their own data. There is a test for both halves of this.

---

## REAL vs STUB — read this before believing anything

### REAL (built, and covered by passing tests)

- RFC4180 CSV ingest with header aliasing, date-order auto-detection, EU decimals, parenthesised
  negatives; unreadable rows flagged with CSV line numbers, never dropped.
- Client-key normalization (corporate-suffix stripping, `&`/`and` folding, leading "The"),
  multi-spelling merge with disclosure.
- Concentration arithmetic: shares, top-N, HHI, effective client count, 50%/80% thresholds.
  Verified against hand-computed cases (single client → HHI 10,000; four equal clients → HHI 2,500).
- Credits netted against the issuing client; net-negative clients excluded from share math but
  still listed.
- Per-client dormancy against that client's own median gap; payment timing from a paid-date column.
- Monthly series that reconciles to the file total (asserted in tests).
- **Dependency-free** XLSX writer and one-page PDF renderer, both byte-deterministic; XLSX verified
  by walking the central directory and inflating every part, PDF verified by checking every xref
  offset resolves to a real object header and that `/Length` matches the true stream byte length.
- Fail-closed advice linter with the lint-safe-twin design described above.
- Full checkout → signed webhook → entitlement → gated delivery loop, plus the free preview.

### STUB / by design — NOT real

- **No live Stripe account, price, or keys. Nothing is deployed.** Every payment path returns
  `501 not_configured` until the founder sets env vars. **$0 has been earned.**
- **Stripe is MOCKED in the tests.** `test/buyloop.test.js` replaces the `stripe` module and runs
  the entitlement store in memory. It is a logic-level proof that the paths are coherent and fail
  closed — it is **not** a live run and **not** a real Stripe test-mode run.
- **Client grouping is string matching only.** There is no company database. Two genuinely
  different clients with near-identical names could merge; a heavily abbreviated name may not. Every
  merge is disclosed so the buyer can check it, but the engine cannot know it was wrong.
- **The corporate-suffix list is fixed and Latin-alphabet biased.** Non-Western entity suffixes are
  not stripped.
- **No enrichment of any kind** — no industry, no size, no external lookup. Figures reflect only the
  rows in the uploaded file. Revenue invoiced outside that file is invisible.
- **The in-memory entitlement store is not durable in serverless.** Without Vercel KV a cold start
  loses a buyer's unlock. Set KV **before taking real money** (the Stripe-session verification path
  is a second line of defence, but KV is the correct fix).
- Concentration metrics are descriptive statistics, not a model of anything. HHI is reported with
  its scale explained; the engine attaches no judgement to any value.

---

## Bug fixed here that is still present in the sibling products

`api/webhook.js` in `hff-recurring-charges`, `hff-invoice-aging`, `hcf-phish-checker` and
`hrf-compliance-digest` assigns `module.exports.config = {...}` **before** `module.exports = handler`.
The second assignment replaces the exports object and silently discards `config`, so
`bodyParser: false` never takes effect. In production Vercel would hand the handler a parsed body,
the raw bytes needed for signature verification would be gone, and **every Stripe webhook signature
check would fail**.

This product assigns `config` **after** the handler and has a regression test for it
(`REGRESSION: webhook exports config with bodyParser disabled`). The siblings are **not** fixed —
writes for this run were scoped to this product folder. Fixing them is a separate, deliberate change.

---

## Layout

```
engine/
  constants.js       product name, disclaimer, suffix list, thresholds
  validate.js        input gate (size / row caps), fails closed with codes
  ingest.js          RFC4180 parse, header aliasing, dates, amounts, client keys
  concentration.js   client rollup, shares, HHI, dormancy, monthly series
  summary.js         factual narrative + lint-safe twins
  advice_linter.js   HARD GUARDRAIL, fail-closed
  render_xlsx.js     dependency-free 5-sheet XLSX writer
  render_pdf.js      dependency-free one-page PDF renderer
  zip.js             dependency-free ZIP/DEFLATE writer
  index.js           pipeline entry point
  sample/            sample_invoices.csv (used by both test suites)
api/
  preview.js                  FREE, ungated top-line figures
  create-checkout-session.js  Stripe Checkout ($9 one-time), 501 until keys
  webhook.js                  signature-verified entitlement grant, fails closed
  entitlement.js              GET /api/entitlement?session_id=…
  generate-report.js          PAID full report + XLSX/PDF, gated
lib/store.js                  Vercel KV when configured, in-memory otherwise
public/index.html             landing page + free preview
public/success.html           post-purchase report generation + downloads
```

## Tests

```bash
node test/engine.test.js     # 48 assertions — engine, guardrail, XLSX, PDF
node test/buyloop.test.js    # 32 assertions — checkout, webhook, entitlement, gating, preview
npm test                     # both
```

No `npm install` needed. No network. No keys. Node 22+.

---

## Founder go-live

Nothing below has been done. All of it is a founder gate.

1. **Create the price** — in Stripe, a **$9 one-time** price for "Client Revenue Concentration
   Report". Copy the `price_…` ID.
2. **Set env vars** in Vercel (Project → Settings → Environment Variables):
   `STRIPE_SECRET_KEY`, `STRIPE_PRICE_REPORT`, `STRIPE_WEBHOOK_SECRET`, `BASE_URL`,
   and — **before taking real money** — `KV_REST_API_URL` + `KV_REST_API_TOKEN`.
3. **Add the webhook endpoint** in Stripe pointing at `<BASE_URL>/api/webhook`, subscribed to
   `checkout.session.completed`. Copy its signing secret into `STRIPE_WEBHOOK_SECRET`.
4. **Deploy** via the guard-railed pipeline: `scripts/factory_deploy.sh` — never a bare
   `vercel deploy --prod`.

Until step 2, the product is inert: checkout, webhook and paid generation all return
`501 not_configured`. The free preview works without any keys.
