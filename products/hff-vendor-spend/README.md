# HFF — Vendor Spend Rollup (`hff-vendor-spend`)

Upload an expense, bill, or card CSV. Get back a rollup of what each vendor was
actually paid — net of credits — with payment cadence, amount drift, monthly
totals, and a category breakdown. Delivered as a 6-sheet XLSX workbook and a
one-page PDF summary.

**Price:** $9, one-time, no account.
**Factory:** HFF (Hoch Finance Factory).
**Guardrail:** organizational tooling only; no financial/tax/legal advice; never
tells the buyer which vendors to cut, keep, or renegotiate.

---

## Status: CODE-COMPLETE at the doorstep

Built by the autonomous factory loop. It is **not deployed and has earned $0.**
The only thing standing between this folder and a live checkout is the founder
gate at the bottom of this file.

---

## REAL vs STUB — no fake green

### REAL (implemented, tested, runs today)

| Piece | Notes |
|---|---|
| CSV ingest | RFC4180 quoting, CRLF, BOM, header aliasing, ISO/US/UK dates with whole-file order detection, EU decimal commas, currency symbols, parenthesised and trailing-minus negatives, separate debit/credit columns. |
| Row accounting | Unreadable rows are **flagged with their CSV line number and a reason**, never silently dropped. Accepted and skipped sets are disjoint (tested). |
| Vendor grouping | String normalization only — corporate suffixes, leading "The", card-processor prefixes (`SQ *`, `PAYPAL *`), trailing store numbers. Every merge is disclosed in the report. **There is no vendor database behind this.** |
| Spend analysis | Per-vendor gross / credits / net, share of total, payment count, min / median / max payment, first and last payment, months active. |
| Cadence & dormancy | Median gap between a vendor's own payments (needs ≥3 payments); "quiet vs own rhythm" when the gap since the last payment exceeds 2.5× that vendor's own median gap. |
| Amount drift | Arithmetic difference between the first and last recorded payment per vendor. Stated as arithmetic, never as a price judgement. |
| Concentration | Top 1/3/5/10 share, HHI on the 0–10,000 scale, effective vendor count, and how few vendors make up the first 50% / 80%. No threshold, no judgement attached. |
| Monthly + category rollups | Category labels reproduced exactly as the file wrote them. |
| Advice linter | **Hard guardrail, fails closed.** Runs before any artifact bytes are produced. Vendor-name-bearing notes are linted via lint-safe twins so a buyer whose vendor is literally named "Cut Costs Consulting" is not blocked by their own data. |
| XLSX writer | Real SpreadsheetML package, hand-built, **zero npm dependencies**. Six sheets. Verified by inflating the ZIP in tests, not by string-searching compressed bytes. |
| PDF writer | Real PDF 1.4, Helvetica base-14, **zero npm dependencies**, byte-deterministic. |
| Free preview endpoint | Ungated, runs the real engine, returns a genuine subset. Verified against a direct engine run so it cannot drift into fabrication. |
| Checkout endpoint | Stripe Checkout session creation. **Inert 501 without keys.** |
| Webhook | Signature-verified via `STRIPE_WEBHOOK_SECRET`, **fails closed (400)** on a bad or missing signature. `config.bodyParser=false` is assigned *after* `module.exports` so it survives — there is a regression test for exactly this. |
| Entitlement store | `lib/store.js`: `@vercel/kv` when `KV_REST_API_URL` + `KV_REST_API_TOKEN` are set, in-memory `Map` otherwise. |
| Gated delivery | Three-path gate: store entitlement → live Stripe session verification → dev unlock. Fails closed (402 / 501). |

### STUB / NOT BUILT — stated plainly

| Piece | Reality |
|---|---|
| Deployment | **Not deployed.** No Vercel project, no domain, no live URL. |
| Stripe price | **Does not exist.** `STRIPE_PRICE_REPORT` has no real value yet. |
| Durable entitlements | Without KV credentials the store is an **in-memory Map that does not survive a serverless cold start.** Fine for tests and local use; a real buyer needs KV set. |
| Currency conversion | **Not implemented and never will be silently.** If the file names more than one currency the report says so explicitly and refuses to imply the totals are meaningful. |
| Vendor identity resolution | **Not implemented.** Grouping is string matching. Two genuinely different vendors with the same normalized name will merge; the merge is always disclosed. |
| Revenue | **$0.** Nothing has been sold. |

---

## Layout

```
engine/     ingest.js  spend.js  summary.js  advice_linter.js
            render_xlsx.js  render_pdf.js  zip.js  validate.js  constants.js
            sample/sample_expenses.csv
api/        preview.js (free)  generate-report.js (paid)
            create-checkout-session.js  webhook.js  entitlement.js
lib/        store.js
public/     index.html  success.html
test/       engine.test.js  buyloop.test.js
```

## Running the tests

No install needed — the engine and both suites are dependency-free.

```bash
cd products/hff-vendor-spend
node test/engine.test.js
node test/buyloop.test.js
```

`npm test` runs both. (`npm install` is only needed for the `stripe` package,
which the API routes `require` lazily and only when a key is set.)

## Local dry run without paying

```bash
VENDORSPEND_DEV_UNLOCK=1 node -e "
  const {buildReport}=require('./engine');
  const fs=require('fs');
  const {report,xlsx,pdf}=buildReport(fs.readFileSync('engine/sample/sample_expenses.csv','utf8'));
  fs.writeFileSync('/tmp/rollup.xlsx',xlsx); fs.writeFileSync('/tmp/rollup.pdf',pdf);
  console.log('net', report.summary.spend.net, 'vendors', report.summary.counts.vendors);
"
```

---

## FOUNDER GATE — the only steps left, and they are all yours

The build loop stops here by design. It never handles keys, never deploys, never
moves money. Each step below requires your authentication or your click.

1. **Create the Stripe price.** In the Stripe dashboard create a **one-time**
   product at **$9** and copy its `price_...` ID.
2. **Create the Vercel project** pointed at `products/hff-vendor-spend`, and set
   these environment variables in the Vercel UI (never in this repo):
   - `STRIPE_SECRET_KEY` — your `sk_live_...`
   - `STRIPE_PRICE_REPORT` — the price ID from step 1
   - `STRIPE_WEBHOOK_SECRET` — from step 4
   - `BASE_URL` — the deployed URL
   - `KV_REST_API_URL` + `KV_REST_API_TOKEN` — strongly recommended, otherwise
     entitlements do not survive a cold start
3. **Deploy through the guard-railed pipeline only:**
   ```bash
   scripts/factory_deploy.sh products/hff-vendor-spend
   ```
   Source-match guard → preview → smoke test → promote → auto-rollback. Do not
   run `vercel deploy --prod` from an unverified folder.
4. **Add the Stripe webhook endpoint** at `https://<your-domain>/api/webhook`
   subscribed to `checkout.session.completed`, then put its signing secret into
   `STRIPE_WEBHOOK_SECRET` and redeploy.
5. **Verify the loop end to end** with a Stripe test-mode purchase before going
   live: preview → checkout → webhook grant → `/api/entitlement` reports paid →
   `/api/generate-report` returns both files.

Until step 5 passes against real Stripe evidence, this product's status stays
`3_PRODUCTIZED_CODE_COMPLETE` and its settled revenue stays `$0.00`.
