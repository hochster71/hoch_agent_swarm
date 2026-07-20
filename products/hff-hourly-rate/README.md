# HFF — Effective Hourly Rate Report

**Upload a time-tracking CSV → see what your tracked hours actually earned.**
$9 one-time. No account, no bank connection, no stored file.

Status: **CODE-COMPLETE (doorstep).** Built and tested by the HELM autonomous factory loop.
**$0 earned. Nothing deployed. No Stripe price, no keys.** Only a founder deploy remains — see
[Founder go-live](#founder-go-live).

---

## What it does

A stranger pastes or uploads a time-tracking export (Toggl, Harvest, Clockify or any CSV with a
date, a client and a duration). The deterministic engine returns:

* **Per-client breakdown** — hours, share of tracked time, entries, billable vs non-billable
  hours, observed revenue, rate per covered hour, blended rate across all hours, median and
  longest session, months active, project count, first and last entry.
* **Two honest rates** — `effective rate per covered hour` (revenue ÷ hours of the entries that
  carry billing figures) and `blended rate` (revenue ÷ every tracked hour). The report states
  exactly what share of hours had billing data, so neither number can quietly overstate.
* **Billable share** — over hours with a *readable* billable flag only; unreadable flags are
  counted in totals and disclosed, never guessed.
* **Monthly + weekday series** — hours, billable share, revenue and active clients per month;
  hours by weekday.
* **Spelling merges** — "Acme Corp" / "ACME CORPORATION" group into one client; every merge is
  disclosed. String matching only; no company database.
* **Flagged rows** — every unreadable row with its CSV line number and reason
  (`unreadable_date`, `zero_duration`, `implausible_duration`, …). Nothing silently dropped.
* **Artifacts** — a 5-sheet XLSX workbook (Summary, Clients, Monthly, All Entries, Flagged Rows)
  and a one-page PDF, both dependency-free and byte-deterministic.

Durations accepted: decimal hours (`3.5`, EU `3,5`), clock form (`3:30`, `3:30:00`),
word form (`7h 30m`, `45 min`), or a minutes-unit column. Amount and rate columns are optional;
when only a rate exists, figures are computed as rate × hours and disclosed as derived.

## Guardrail (enforced in code)

Organizational tooling only. A **fail-closed advice linter** runs on every engine-authored
sentence *before* any artifact bytes are rendered. Banned: what to charge, judgement about a
rate (undercharging, too low, below market…), client keep/drop instructions, and any
recommendation framing. A violation withholds the entire report — paid or free (HTTP 422).
Notes embedding a buyer's client name are linted against a `<client>`-substituted twin, so a
client literally named "Charge More LLC" cannot false-positive a paid report away.

## The buy loop (mirrors hff-runway / hff-client-concentration)

1. `public/index.html` — landing page + **free ungated preview** (`/api/preview`, a genuine
   subset of the paid run).
2. `POST /api/create-checkout-session` — $9 one-time Stripe Checkout (`501` until keys set).
3. `POST /api/webhook` — signature-verified (fails closed 400; inert 501 without keys). Grants
   `sess:<checkout_session_id>` in `lib/store.js` (Vercel KV, or in-memory fallback).
   **Note:** `module.exports.config` is assigned *after* the handler so `bodyParser:false`
   survives — regression-tested; some sibling products have this bug.
4. `GET /api/entitlement?session_id=…` — paid check.
5. `POST /api/generate-report` — entitlement-gated full report + XLSX/PDF (base64).
   `HOURLYRATE_DEV_UNLOCK=1` allows local testing, labelled `dev`, never a real payment.

## REAL vs STUB (honest inventory)

**REAL:** RFC4180 ingest (quoting, CRLF, BOM, header aliasing, ISO/US/UK date auto-detect,
EU decimals), duration parser (clock/word/decimal/minutes forms; zero and >24h entries flagged),
billable-flag parser, negative-amount exclusion with disclosure, client-key normalization with
disclosed merges, rate arithmetic verified against hand-computed cases, monthly/weekday series
that reconcile to file totals, fail-closed advice linter, dependency-free byte-deterministic
XLSX writer and PDF renderer (XLSX verified by walking the central directory and inflating
every part; PDF verified by resolving every xref offset), full checkout → webhook →
entitlement → gated delivery loop, free preview proven a subset of the paid run.

**STUB / BY DESIGN:** no live Stripe account, price, keys, or deploy — every payment path
returns `501 not_configured` until env vars are set; Stripe is **mocked** in tests and the
store runs in-memory (NOT a live or Stripe-test-mode run); the in-memory store is not durable
across serverless cold starts (set up Vercel KV before taking real money); rates are arithmetic
over the uploaded file only — no market-rate data, no benchmarking, no enrichment; client
grouping is string matching only.

## Tests

```bash
node test/engine.test.js    # engine: ingest, durations, rates, linter, XLSX, PDF, sample
node test/buyloop.test.js   # buy loop: checkout/webhook/entitlement/delivery, fail-closed paths
```

No install, no network, no keys required (node v22+).

## Founder go-live

1. Create a **$9 one-time** Stripe Price for "Effective Hourly Rate Report"; note the
   `price_…` id.
2. In Vercel project env vars set: `STRIPE_SECRET_KEY`, `STRIPE_PRICE_REPORT`,
   `STRIPE_WEBHOOK_SECRET` (after step 4), `BASE_URL`, and (before real money)
   `KV_REST_API_URL` + `KV_REST_API_TOKEN`.
3. Deploy via `scripts/factory_deploy.sh` (guard-railed pipeline; never raw
   `vercel deploy --prod`).
4. In the Stripe Dashboard add a webhook endpoint for `checkout.session.completed` pointing at
   `https://<deployment>/api/webhook`; put its signing secret in `STRIPE_WEBHOOK_SECRET` and
   redeploy.
5. Verify: free preview works; buy with a live card; success page generates and downloads both
   files. Until then every paid path honestly returns 501/402.
