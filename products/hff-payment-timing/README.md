# Getting-Paid Speed Report (`hff-payment-timing`)

Upload an invoice CSV → a deterministic picture of **how fast your clients actually pay once billed**, as a 5-sheet XLSX workbook and a one-page PDF. Organizational tooling only — **not** financial, tax, legal, or collections advice.

Part of the **Hoch Finance Factory (HFF)**. Mirrors the proven `hff-vendor-spend` pattern: real engine → free preview → `create-checkout-session` → signature-verified `webhook` → entitlement store → gated delivery.

Price: **$9 one-time**.

---

## What it does (REAL)

Given a CSV with an **issue date**, a **client**, an **amount**, and a **paid-date** column (a blank paid date = the invoice is still open), the engine computes, purely arithmetically over the rows it accepts:

- **Per client:** amount billed and share of billing; invoice / paid / open counts; amount paid and amount still outstanding; **median / mean / fastest / slowest days-to-pay** across that client's paid invoices; on-time vs late counts; open invoices past due; oldest open invoice age; and every spelling that merged into the bucket.
- **Overall:** median & mean days-to-pay, on-time share, share of billing collected by count and by value, total outstanding, how much of it is past due, oldest open age.
- **Monthly series** by issue month (invoices, billed, paid, median days-to-pay, on-time share).
- **Billed concentration:** top-1/3/5 share, HHI on the 0–10,000 scale, effective client count.
- **Due basis, disclosed:** each invoice's due date comes from a due-date column if present, else from parseable terms (`Net 30`, `Due on receipt`, …), else from an **assumed net-30** — and the report tells you how many invoices fell into each bucket.

Ingest handles RFC-4180 quoting, CRLF, BOM, header aliasing, ISO/US/UK dates (auto-detected), EU decimals, currency symbols, and parenthesised negatives. **Unreadable rows are flagged with their CSV line number, never silently dropped.** Negative amounts are treated as credit notes, disclosed, and kept out of the timing math. A payment dated before its invoice is flagged, not counted.

Outputs are **byte-deterministic**: the XLSX and PDF are hand-built with no npm dependency (the only production dependency is `stripe`, used solely by the payment endpoints).

### Hard guardrail

A fail-closed **advice linter** runs over every engine-authored string *before any artifact bytes are produced*. It withholds the whole report (HTTP 422) if wording ever drifts into telling the reader to chase a client, add a fee, or drop a client, or into judging a client. Neutral factual descriptors (`paid late`, `overdue`, `still open`) are allowed. Notes that embed a client's real name carry a lint-safe twin (`<client>`), so a buyer whose client is literally named "Chase Them Consulting" is not blocked by a false positive on their own data.

---

## What is a STUB / by design

- **No live Stripe account, price, keys, or deployment.** Every payment path returns **HTTP 501 `not_configured`** until the founder sets env vars. The free preview works without any keys.
- Tests **mock** Stripe and run the entitlement store **in-memory** — this is not a live or Stripe-test-mode run.
- Detection is **arithmetic over your file only** — no bank/accounting connection, no client database, no benchmarking, no market comparison. Client grouping is string matching; near-identical distinct clients could merge and abbreviations may not.
- The in-memory entitlement store is **not durable across serverless cold starts** — Vercel KV is required before taking real money.
- `assumed net-30` is exactly that: an assumption applied only where the file gives no due date or terms, and it is disclosed in the report.

---

## Test results (real)

```
node test/engine.test.js   → 58 passed, 0 failed
node test/buyloop.test.js   → 25 passed, 0 failed
```
Run on Node v22.22.3, no install, no network, no keys. (`npm test` runs both.)
The one `Cannot find module 'stripe'` log line during the webhook test is expected — with no `npm install`, the webhook still **fails closed** (400 invalid_signature), which the test asserts.

---

## Founder go-live (the only remaining step)

This product is code-complete to the doorstep. To take it live:

1. **Create a $9 one-time Stripe Price** in the founder's Stripe account; note the `price_…` id.
2. **Set env vars** in Vercel (see `.env.example`):
   - `STRIPE_SECRET_KEY` (founder's key — never committed)
   - `STRIPE_PRICE_REPORT` (the price id from step 1)
   - `STRIPE_WEBHOOK_SECRET` (from the webhook endpoint in step 4)
   - `BASE_URL` (the deployment URL)
   - `KV_REST_API_URL` + `KV_REST_API_TOKEN` (Vercel KV — **required before real money** so entitlements survive cold starts)
3. **Deploy** via `scripts/factory_deploy.sh` (guard-railed preview → smoke → promote). Do **not** `vercel --prod` from an unverified folder.
4. **Add a Stripe webhook** to `https://<deployment>/api/webhook` for `checkout.session.completed`, and paste its signing secret into `STRIPE_WEBHOOK_SECRET`.

Until then the app is inert on all paid paths (501) and the free preview is fully functional.

## Endpoints

- `POST /api/preview` — free, ungated: top-line figures + first three clients (a genuine subset of the paid run).
- `POST /api/create-checkout-session` — `{ tier: "report" }` → `{ url }` (501 until keys set).
- `POST /api/webhook` — Stripe signature-verified; grants `sess:<id>` on `checkout.session.completed`.
- `GET  /api/entitlement?session_id=…` — `{ paid: boolean }`.
- `POST /api/generate-report` — entitlement-gated: full JSON + XLSX + PDF (base64).
