# HRF — Clarity Briefs

**"The truth, in plain English, with receipts."**

Short, cited, jargon-free research briefs on the topics that shape real decisions —
health, money, policy, tech. Every claim links to a real source; every brief ends with
an explicit "what's still uncertain" section.

- **Price:** $5/mo subscription, or $2 per one-off brief.
- **Buyer:** curious non-experts, teachers, caregivers, small-business owners, journalists.
- **Registry:** `coordination/products/product_registry.json` → `HRF_CLARITY_BRIEFS` (spec: `docs/products/HCF_HRF_PRODUCT_SPECS.md`).

## Guardrail (honored)

Briefs **summarize and cite existing public sources** with a citation-per-claim rule and a
mandatory uncertainty section — clarity with receipts, not hot takes. They are information,
**not professional (medical/legal/financial) advice**. This disclaimer is shown on the landing
page and must appear on every generated brief. Same honesty doctrine as HELM: label what you
don't know; no false confidence.

## The engine (built)

The brief generator now exists in `engine/`. It is a **research → cited-brief
verifier**: given a topic + INPUT SOURCES + drafted claims, it produces a
structured brief where **every claim carries an inline citation**, enforces that
rule with a fail-closed linter, and emits Markdown + HTML + a `brief.json`
sidecar. Run it:

```bash
cd products/hrf-clarity-briefs
python3 -m unittest discover -s tests -v          # 7/7 pass (linter proof)
python3 -m engine.cli --request examples/request.sample.json --out out/
```

Pipeline: `retrieval` (sources in) → `engine.generate_brief` (assemble + auto-seed
uncertainty + **lint, fail-closed**) → `assembler` (MD/HTML/JSON). Gated by
`entitlement` (checkout token; no real payment).

## What is REAL vs STUB (NO FAKE GREEN)

**REAL (works as written, verified by running it):**
- **Citation-coverage LINTER** (`engine/linter.py`) — the moat. Fails the brief if
  ANY claim lacks a citation, if a citation points to an unknown source, if a
  quote is not found **verbatim** in its source (anti-fabrication), or if the
  uncertainty section / disclaimer is missing. Proven by `tests/test_linter.py`:
  `test_catches_uncited_claim` shows an injected uncited claim drops coverage to
  75% and the brief does NOT render. **7/7 tests pass.**
- **Brief assembler** (`engine/assembler.py`) — sources + claims in →
  Markdown + HTML + `brief.json`, numbered live-link references, inline `[n]`
  markers, mandatory disclaimer banner + uncertainty section.
- **Orchestrator** (`engine/engine.py`) — fails closed on any lint violation;
  auto-seeds the uncertainty section so it is never empty-by-omission.
- **Entitlement gate** (`engine/entitlement.py`) — file-backed token store wired
  to the checkout shape; one-off credits are consumed, subscriptions unlimited.
  **No real payment.**
- **CLI** (`engine/cli.py`) — end-to-end runnable; writes timestamped artifacts.
- Deployable static landing page (`public/index.html`), working Buy buttons.
- `POST /api/create-checkout-session` — reads `STRIPE_SECRET_KEY` +
  `STRIPE_PRICE_MONTHLY`/`STRIPE_PRICE_BRIEF` from env, returns `{ "url": ... }`.
  Fails safe with a 501 when keys are absent (INERT until the founder sets keys).
- **`POST /api/webhook`** (`api/webhook.js`) — verifies the Stripe signature
  (`STRIPE_WEBHOOK_SECRET`) with a zero-dependency HMAC implementation of Stripe's
  v1 scheme (constant-time compare + timestamp tolerance), **fails closed** (400)
  on a bad/missing signature, and on `checkout.session.completed` **grants an
  entitlement token** (the checkout session id) into the SAME JSON store the Python
  gate reads (`lib/entitlements.js` → `HRF_ENTITLEMENTS_PATH`; `brief`→1 credit,
  `monthly`→unlimited). 501 until `STRIPE_WEBHOOK_SECRET` is set. Proven by
  `tests/test_webhook.mjs` (14 assertions, incl. a cross-language check that the
  Python gate accepts+consumes the granted token).
- **`POST /api/generate`** (`api/generate.py`) — the delivery route: an entitled
  token + topic + sources + drafted claims runs the real engine and returns the
  rendered brief; 402 un-entitled, 422 fail-closed on an uncited claim. Proven by
  `tests/test_generate.py` (5 tests).
- **`public/request.html`** — the redeem/generate page (token + topic + sources +
  claims → rendered brief inline); `success.html` surfaces the token; `index.html`
  links to it.
- `vercel.json` (JS + Python functions), `requirements.txt`, `.env.example`
  (placeholders only), success page.

**STUB / INTEGRATION POINTS (must not be claimed as done — no fabrication):**
- **Live source gathering** (`engine/retrieval.py` → `LiveWebSourceProvider`) is
  **not wired**; it raises rather than inventing sources. The engine runs today
  on **provided** sources. Auto-gather means running the repo's real `WebSearch`
  / `web_fetch` tools + research MCPs (PubMed, bioRxiv, Consensus,
  ClinicalTrials) and capturing url + title + retrieved-at + fetched text.
- **LLM claim composition** — turning raw sources into draft claims is an LLM
  "compose" step. The engine **verifies** drafted claims; it does not invent
  them. Semantic support-checking (does this quote actually *support* the claim,
  beyond appearing in the source) is the LLM "council" fact-check pass — a
  documented second pass, not bundled in the deterministic core.
- **PDF** — HTML output is print-ready; PDF conversion is an optional handoff to
  the `anthropic-skills:pdf` skill or any html→pdf tool (keeps the core
  dependency-free).
- **Durable shared store on Vercel** — the webhook and the generate route share a
  file-backed store (`HRF_ENTITLEMENTS_PATH`). This is durable on any host with a
  persistent writable filesystem, but Vercel's serverless filesystem is ephemeral
  per-invocation, so on Vercel this path must point at a mounted/persistent volume
  (or `lib/entitlements.js` be swapped for a KV backend). The JSON format contract
  with the engine does not change either way.
- **Email/reader delivery** — the brief is returned to the browser and rendered
  inline; emailing it or hosting a reader is not built.

## Remaining work to make it genuinely sellable

1. **Wire live retrieval** — implement `LiveWebSourceProvider.gather` against the
   real `WebSearch`/`web_fetch`/research-MCP path (the only thing standing between
   "verifies your sources" and "gathers its own").
2. **Wire the LLM compose + council fact-check** so a bare topic (no hand-fed
   claims) produces the draft the linter then polices.
3. ~~Add `/api/webhook` → write tokens into the entitlement store; add delivery.~~
   **DONE** — `api/webhook.js` + `api/generate.py` + `public/request.html`. Still
   open: durable shared store on Vercel (persistent volume or KV) and email/reader
   delivery (see STUB list).
4. **Founder-gated:** create the two Stripe Prices ($5/mo, $2 one-off), set env
   vars (`STRIPE_SECRET_KEY`, `STRIPE_PRICE_*`, `STRIPE_WEBHOOK_SECRET`, `BASE_URL`,
   `HRF_ENTITLEMENTS_PATH`), add the webhook endpoint in Stripe, and deploy to
   Vercel via the guard-railed pipeline.
5. Pick one concrete launch vertical (e.g. "everyday health claims, decoded").

## Founder step to go live (exact)

1. In Stripe (test first), create two Prices: $5/mo recurring, $2 one-off. Copy
   their IDs.
2. In Vercel project env, set `STRIPE_SECRET_KEY`, `STRIPE_PRICE_MONTHLY`,
   `STRIPE_PRICE_BRIEF`, `BASE_URL`.
3. Deploy via `scripts/factory_deploy.sh` (never `vercel deploy --prod` from an
   unverified folder).
4. Do the two integration-point wirings above (retrieval + compose) so a buyer's
   topic yields a real brief; today the engine requires provided sources/claims.

## Local shape

```
products/hrf-clarity-briefs/
  engine/
    schemas.py           dataclasses: Source, Citation, Claim, Brief, BriefRequest
    linter.py            citation-coverage linter (the moat) + quote grounding
    assembler.py         Brief -> Markdown / HTML / brief.json
    retrieval.py         provided sources (REAL) + live-web integration point (stub)
    entitlement.py       checkout-token gate (no real payment)
    engine.py            orchestrator (assemble -> lint fail-closed)
    cli.py               python -m engine.cli --request ... --out ...
  tests/test_linter.py   proves the linter catches an uncited claim (7 tests)
  examples/              request.sample.json + entitlements.sample.json (fixtures)
  public/index.html      landing page + Buy buttons
  public/success.html    post-checkout thank-you
  api/create-checkout-session.js   POST -> { url }
  vercel.json
  .env.example
  package.json
```

Do **not** run `vercel deploy --prod` from here without the guard-railed pipeline. No keys are set;
no Stripe objects are created by this repo.
