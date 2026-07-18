# HFF — Recurring Charge Finder

**$9 one-time.** Upload a bank or card CSV → every charge that repeats, with its
cadence, typical amount, price drift, and annualized cost, delivered as an XLSX
workbook and a one-page PDF.

**Status: CODE-COMPLETE (rung 3). Not deployed. $0 earned. No live Stripe keys.**
Built to the doorstep by the autonomous factory loop; the go-live step is the
founder's, and only the founder's.

---

## Guardrail

> Organizational tooling only — **no financial, tax, or legal advice.**

Enforced mechanically, not by convention. `engine/advice_linter.js` scans every
user-visible string (merchant labels, summary headlines, observations, the
disclaimer) *before* any artifact bytes are rendered, and **fails closed**: a
banned phrase throws `ADVICE_LINTER_FAILED` and the whole report is withheld.
Paying does not buy past the guardrail — the paid endpoint returns `422` with no
files attached (covered by a test).

The engine describes what it observed ("latest charge is 16.1% higher than the
first observed charge") and never what to do about it.

---

## REAL vs STUB — read this before believing anything

### REAL (built, exercised by tests)
- **Ingest** — RFC4180 CSV parsing (quotes, escaped `""`, CRLF, BOM), header
  aliasing across common bank/card exports, ISO / US / UK dates with automatic
  order detection, currency symbols, thousands separators, EU decimal commas,
  parenthesised and trailing-minus negatives.
- **Flagged rows** — unreadable rows are reported with their CSV line number and
  a machine-readable reason. Nothing is silently dropped.
- **Merchant normalization** — collapses processor prefixes (`SQ *`, `TST*`,
  `PP*`, `POS DEBIT`), store numbers, reference codes, masked card tails, domain
  tails and trailing US-state tokens so the same merchant groups together.
- **Cadence detection** — median-interval classification into weekly, biweekly,
  monthly, quarterly, semiannual, annual, or irregular; confidence scored from
  occurrence count, interval consistency, and amount stability.
- **Observations** — price drift vs the first charge, patterns that stopped
  charging earlier than their own cadence predicts, and category-tag overlap
  between two or more distinct merchants in the same file.
- **Renderers** — dependency-free XLSX writer (real SpreadsheetML package: content
  types, rels, styles, four worksheets, inline strings) and a dependency-free
  one-page PDF. Both are **byte-deterministic** for a given input.
- **Buy loop** — checkout-session creator, signature-verified Stripe webhook,
  entitlement store (Vercel KV when configured, in-memory otherwise),
  entitlement route, entitlement-gated report endpoint, free ungated preview,
  landing page and delivery UI.

### STUB / by design
- **No live Stripe account, price, or keys, and no deploy.** Every payment path
  is inert (`501 not_configured`) until the founder sets env vars.
- **Buy-loop tests MOCK Stripe** (no network, no keys) and run the store on its
  in-memory fallback. They prove the code paths are coherent; they are **not** a
  live run and not a real Stripe test-mode run.
- **Detection is deterministic and statistical, not semantic.** It groups by
  normalized merchant string and interval regularity. It has no merchant
  database, no bank connection, and no knowledge of what a subscription "is". A
  merchant that changes its descriptor format mid-file may split into two groups;
  two unrelated merchants with near-identical names may merge. Confidence is
  reported per pattern so the buyer can see how sure the engine is.
- **Overlap tags** are a fixed keyword list (`engine/constants.js`), not a
  taxonomy. Absence of a tag means nothing.
- **The engine only ever sees the file you give it.** No enrichment, no lookups.

---

## Layout

```
engine/
  constants.js        product strings, cadence buckets, overlap tags, disclaimer
  validate.js         input gate (size, type, row cap) — fails closed
  ingest.js           CSV parse, header aliasing, date/amount parsing, row flagging
  recurring.js        merchant normalization, cadence detection, confidence scoring
  summary.js          factual summary + observation strings
  advice_linter.js    HARD GUARDRAIL, fails closed
  zip.js              dependency-free ZIP writer (CRC-32 + DEFLATE)
  render_xlsx.js      dependency-free XLSX package builder
  render_pdf.js       dependency-free one-page PDF
  index.js            analyze() / buildReport() pipeline
  sample/             two real sample CSVs used by the tests
api/
  create-checkout-session.js   $9 one-time Stripe Checkout (501 without keys)
  webhook.js                   signature-verified; grants sess:<id> (400 on bad sig)
  entitlement.js               GET /api/entitlement?session_id=...
  preview.js                   FREE, ungated top-line preview
  generate-report.js           PAID, entitlement-gated full report + XLSX + PDF
lib/store.js                   @vercel/kv when configured, in-memory otherwise
public/                        index.html (landing + preview), success.html (delivery)
```

## Tests

```
npm test          # node test/engine.test.js && node test/buyloop.test.js
```

No install and no network required — `stripe` is mocked in the buy-loop tests and
the engine has zero runtime dependencies.

Recorded run on **node v22.22.3**:

```
engine.test.js   # tests 28   # pass 28   # fail 0
buyloop.test.js  # tests 17   # pass 17   # fail 0
```

---

## FOUNDER GO-LIVE — the only steps left

None of these were taken autonomously. Money, keys, and deploys are founder gates.

1. **Create the price.** In your live Stripe account, create a **$9 one-time**
   price for "Recurring Charge Finder". Copy its `price_…` id.
2. **Set env vars** in the Vercel project (Settings → Environment Variables):
   - `STRIPE_SECRET_KEY` — your live secret key
   - `STRIPE_PRICE_REPORT` — the price id from step 1
   - `STRIPE_WEBHOOK_SECRET` — from the Stripe webhook endpoint you point at
     `/api/webhook` (event: `checkout.session.completed`)
   - `BASE_URL` — the deployed URL
   - optional: `KV_REST_API_URL` + `KV_REST_API_TOKEN` for durable entitlements
     (without them, entitlements live only in process memory and will not
     survive a cold start — set them before taking real money)
3. **Deploy** through the guard-railed pipeline: `scripts/factory_deploy.sh`
   (source-match guard → preview → smoke test → promote → auto-rollback).
   Do not `vercel deploy --prod` from an unverified folder.
4. **Verify** by buying one yourself and confirming the webhook grant lands and
   the delivery page unlocks.

Until step 2 is done every payment path returns `501 not_configured` — the app is
inert by design, not broken. The free preview works without any keys.

`.env.example` contains placeholders only. No key, price, or secret is stored in
this repository.
