# HCF — Email Header Audit

**$5 one-time.** Paste an email's raw header block → an offline, heuristic audit
of who really sent it, what authentication a server *reported*, the delivery path
it took, and every signal worth a second look — each one paired with the ordinary,
benign explanation for it.

**Status: CODE-COMPLETE (rung 3). Not deployed. $0 earned. No live Stripe keys.**
Built to the doorstep by the autonomous factory loop; the go-live step is the
founder's, and only the founder's.

---

## Guardrail

> Heuristic only. Never a claim of certainty. Never a security decision.

Enforced mechanically, not by convention. `engine/report_linter.js` scans the
rendered report *before* it is returned and **fails closed**: a certainty
over-claim ("this email is safe", "100% phishing", "confirmed malicious") or a
directive ("you should delete this", "safe to click") throws
`REPORT_LINTER_FAILED` and the whole report is withheld. Paying does not buy past
the guardrail — the paid endpoint returns `422` with no report attached, and the
free preview is linted on the same code path.

The engine reports what the header text says ("a server reported DMARC=fail") and
never what the message *is* or what to do about it.

---

## REAL vs STUB — read this before believing anything

### REAL (built, exercised by tests)
- **Header parsing** — RFC 5322 folding/unfolding, CRLF and LF, UTF-8 BOM,
  duplicate headers in document order (the Received chain depends on it), the
  blank line that ends the block, RFC 2047 encoded-words (B and Q), and a
  256 KB input cap. Unparseable lines are reported with their line number, never
  silently dropped.
- **Sender resolution** — quote-aware address extraction. A display name that is
  itself a quoted string containing a decoy address
  (`"PayPal <service@paypal.com>" <billing@lookalike.example>`) resolves to the
  **actual** sending domain. A naive first-match regex returns the decoy; that
  inversion is the specific failure this product exists to catch, and it is
  covered by a test.
- **Authentication as reported** — parses `Authentication-Results`,
  `ARC-Authentication-Results`, and legacy `Received-SPF`; prefers the nearest
  non-ARC block; records every distinct authserv-id and flags when more than one
  server made claims. Presented as *claims*, never as verified facts.
- **Alignment checks** — DKIM signing domain, Reply-To, Return-Path, and
  Message-ID each compared against the From domain by approximate registrable
  domain.
- **Lookalike sender domains** — punycode/IDN detection, confusable folding
  (`rn→m`, `0→o`, `1→l`, Cyrillic/Greek homoglyphs) onto a fixed brand list, and
  brand-name-on-someone-else's-domain. Verified against legitimate brand
  subdomains (`mail.google.com`, `em1234.netflix.com`) to keep false positives at
  zero for those cases.
- **Delivery path** — Received hops normalized to chronological order, origin
  identification, public vs private IP extraction, out-of-order clock detection,
  inter-hop gaps, TLS mentions.
- **Scoring** — bounded 0–100 attention score and a LOW/MODERATE/ELEVATED band.
  The band describes how much of the header text warrants a second look; it is
  explicitly **not** a safety rating.
- **Buy loop** — checkout-session creator, signature-verified Stripe webhook,
  entitlement store (Vercel KV when configured, in-memory otherwise), entitlement
  route, entitlement-gated audit endpoint, free ungated preview that exposes
  signal *counts* only, landing page and delivery UI.

### STUB / by design / limits
- **No live Stripe account, price, or keys, and no deploy.** Every payment path
  is inert (`501 not_configured`) until the founder sets env vars.
- **Buy-loop tests MOCK Stripe** (no network, no keys) and run the store on its
  in-memory fallback. They prove the code paths are coherent and fail closed;
  they are **not** a live run and not a real Stripe test-mode run.
- **Nothing is re-verified.** No DNS lookup, no SPF record evaluation, no DKIM
  signature cryptography. The tool reads text. A forged `Authentication-Results`
  header will be read exactly as written — which is why the report frames every
  result as a server's claim and says so in the disclaimer.
- **No message body, link, or attachment is examined.** Header text only.
- **The brand list is fixed and short** (see `engine/constants.js`). A lookalike
  of a brand not on the list will not be flagged as one.
- **Registrable-domain reduction is approximate** — a curated multi-label suffix
  set, not the full Public Suffix List. The report labels it as approximate
  wherever it drives a finding.
- **In-memory entitlement store is not durable across serverless invocations.**
  Configure Vercel KV before taking real money, or a buyer can lose access
  between the webhook and their first request.

---

## Bug found and fixed during this build (worth knowing)

`api/webhook.js` originally set `module.exports.config = { api: { bodyParser: false } }`
*before* `module.exports = handler`, which silently discards the config. In
production that leaves the body parser enabled, destroys the raw body, and makes
**every Stripe signature verification fail**. Fixed here by attaching `config`
after the handler assignment, with a test asserting `webhook.config.api.bodyParser === false`.

**The same ordering appears in the sibling products** (`hff-recurring-charges`,
and by inspection the other buy-loop scaffolds). This build did not modify them —
writes were scoped to this product folder — but the founder should expect the
same fix to be needed there before any of them takes live payments.

---

## Test results (real, from this build)

```
$ npm test          # node v22.22.3, no install, no network, no keys
engine:  51 passed, 0 failed
buyloop: 25 passed, 0 failed
```

Run them yourself: `cd products/hcf-header-audit && npm test`

---

## Layout

```
engine/parse_headers.js   RFC 5322 block parsing, folding, encoded-words
engine/addresses.js       quote-aware address parsing, registrable domains
engine/lookalike.js       punycode, confusable folding, brand adjacency
engine/auth_results.js    Authentication-Results / Received-SPF (as claims)
engine/hops.js            Received chain -> chronological path
engine/checks.js          the heuristic checks (observations, never verdicts)
engine/score.js           bounded score + attention band
engine/report_linter.js   FAIL-CLOSED guardrail
engine/index.js           orchestrator: auditHeaders() / previewHeaders()
api/preview.js            FREE, ungated: identity + signal counts only
api/generate-report.js    PAID: full audit, entitlement gated
api/create-checkout-session.js / api/webhook.js / api/entitlement.js
lib/store.js              KV-or-in-memory entitlement store
public/index.html         landing page + free check
public/success.html       post-purchase delivery UI
```

---

## Founder go-live steps (NOT done, and not doable autonomously)

1. **Create the price** in Stripe: a **$5 one-time** price. Copy its `price_...` ID.
2. **Set env vars** on the Vercel project (never in git):
   - `STRIPE_SECRET_KEY`
   - `STRIPE_PRICE_AUDIT` (the price ID from step 1)
   - `STRIPE_WEBHOOK_SECRET` (from the webhook endpoint you create)
   - `BASE_URL` (the deployed URL)
   - `KV_REST_API_URL` + `KV_REST_API_TOKEN` — strongly recommended before live payments
3. **Add the Stripe webhook endpoint** pointing at `/api/webhook`, subscribed to
   `checkout.session.completed`.
4. **Deploy** via `scripts/factory_deploy.sh` (source-match guard → preview →
   smoke → promote → auto-rollback). Do not `vercel deploy --prod` directly.
5. **Verify the loop** with a real test-mode purchase before flipping to live keys.

Until step 4 completes, this product has earned **$0** and every payment path
answers `501`. That is the honest state.
