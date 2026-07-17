# HRF — Compliance Change Digest ($12/mo)

Given the regulatory / source documents you provide, this produces a **cited,
plain-English digest** of what changed, who it affects, and an explicit
"what we're uncertain about" section — with **citation-per-claim enforced** by a
fail-closed linter.

> **GUARDRAIL (hard):** information, **not legal advice**. Every change-claim must
> carry at least one citation, and every cited quote must appear **verbatim** in
> the source text you supplied, or the digest will not render. The mandatory
> uncertainty section and disclaimer are always present.

This reuses the proven **hrf-clarity-briefs citation-linter** pattern (ported to
Node.js so it runs and tests with zero install and no network).

## What it does (the engine)

`engine/index.js → buildDigest(request)` runs a deterministic, fail-closed pipeline:

- `schemas.js` — the data model: `Source` (a provided doc), `Change` (a
  plain-English claim), `Citation` (`{ source_id, quote }`), `Digest`, and the
  fixed not-legal-advice `DISCLAIMER`.
- `engine.js` — assembles the digest, **auto-seeds** the uncertainty section when
  the author left it empty (only with honest, machine-derived limits: single-source
  claims, unverifiable sources, non-exhaustiveness — it never invents doubts),
  then runs the linter and **throws** if it fails.
- `linter.js` — the moat. Fails closed on: an uncited claim (`COVERAGE`), a
  citation to a non-existent source (`UNRESOLVED_SOURCE`), a quote not found
  verbatim in its source (`UNGROUNDED_QUOTE`, the anti-fabrication check), an empty
  uncertainty section (`EMPTY_UNCERTAINTY`), a missing disclaimer
  (`MISSING_DISCLAIMER`), an empty claim, or zero claims. A shippable digest
  requires **coverage === 100%** and no violations.
- `render.js` — renders Markdown with inline `[n]` footnotes resolving to the
  provided sources, the uncertainty section, and the disclaimer.

## REAL vs STUB

**REAL (works now, tested):**
- The full citation-coverage linter, digest assembler, auto-uncertainty, and
  Markdown renderer (11 engine assertions pass).
- Checkout → signed-webhook → subscription entitlement → gated, repeat digest
  generation (10 mocked buy-loop tests pass).
- Landing page (`public/index.html`) + generation UI (`public/success.html`) with a
  worked example request.

**STUB / by design / founder-supplied:**
- **Deterministic floor only.** Verbatim quote-grounding proves a quote was present
  in the source; it does **not** prove the quote *semantically supports* the claim.
  A deeper LLM "council" fact-check is a documented, optional integration point — it
  is intentionally NOT wired here, so nothing fabricates support.
- **You provide the sources and the drafted changes.** The product does not crawl
  or fetch regulations; it enforces citation discipline over what you give it. (An
  ingestion/summarization front-end is a natural next layer.)
- **No live Stripe account / price / keys and no deploy.** Buy-loop tests MOCK
  Stripe and run the store in-memory. Inert (501) until keys are set.

## Buy-loop architecture (mirrors the proven hff-runway subscription pattern)

- `api/create-checkout-session.js` — `$12/mo` subscription (`mode:'subscription'`).
- `api/webhook.js` — verifies the Stripe signature (fails closed 400); grants
  `email:<addr>` on `checkout.session.completed`, revokes on
  `customer.subscription.deleted`, re-grants/revokes on `.updated`.
- `lib/store.js` — Vercel KV when configured, else in-memory (tests).
- `api/entitlement.js` — `GET ?email=` → `{ paid, tier }`.
- `api/generate-digest.js` — gated: active subscription (by email), or a fresh
  Stripe-verified paid session, or `DIGEST_DEV_UNLOCK=1` (local). Returns **422**
  with the linter violations on a fail-closed digest — never a fake success.

## Tests (run them)

```bash
node test/engine.test.js     # 11 citation-linter / engine assertions
node test/buyloop.test.js    # 10 mocked checkout→webhook→entitlement→gate tests
# or:
npm test
```

Both pass on Node v22 with **no npm install and no network** (Stripe and
`@vercel/kv` are mocked; the store uses its in-memory fallback).

## Founder go-live steps (the only thing left)

1. Create a **$12/mo** recurring price in your Stripe account; note the `price_...` id.
2. In Vercel env vars set: `STRIPE_SECRET_KEY`, `STRIPE_PRICE_MONTHLY`,
   `STRIPE_WEBHOOK_SECRET`, `BASE_URL` (and optionally `KV_REST_API_URL` +
   `KV_REST_API_TOKEN`).
3. Add a Stripe webhook endpoint → `/api/webhook` for `checkout.session.completed`,
   `customer.subscription.deleted`, and `customer.subscription.updated`.
4. Deploy via `scripts/factory_deploy.sh`. Inert (501) until keys set — no fake green.
