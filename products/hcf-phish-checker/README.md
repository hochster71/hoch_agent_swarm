# HCF — Link & QR Safety Report ($5 one-time)

An **offline, heuristic** safety report for a suspicious link or QR code. Paste a
URL (or the decoded contents of a QR) and get a plain-English report covering the
redirect chain, punycode/homoglyph look-alikes, known-bad URL patterns, and the
TLS surface — clearly labeled as a heuristic, **never** a guarantee.

> **GUARDRAIL (hard):** heuristic only. This tool never claims certainty. It runs
> entirely offline (no network fetch), so it cannot see the live page, its
> certificate, or where a shortener/redirect finally lands. A fail-closed
> report-linter (`engine/report_linter.js`) refuses to emit any report that is
> missing the disclaimer or that leaks a certainty over-claim.

## What it does (the engine)

`engine/index.js → generateSafetyReport({ input, kind })` runs a deterministic,
offline pipeline:

- `url_parse.js` — de-noises input (defangs `hxxp://`, `[.]`), tolerates missing
  schemes, and preserves the **raw host** so IDNA normalization can't hide glyphs.
- `homoglyph.js` — punycode (`xn--`) detection + mixed-script / confusable-character
  detection (Cyrillic/Greek letters imitating Latin).
- `heuristics.js` — ~16 checks: no-TLS, raw-IP host, credential/`@` trick,
  brand look-alike (token present but registrable domain isn't the brand's),
  abused TLDs, deep subdomains, URL shorteners (destination **unresolved** offline),
  non-standard ports, heavy percent-encoding, risky download extensions, long/noisy
  domains, **static redirect-chain** extraction from embedded/open-redirect params
  (recursively, no network).
- `score.js` — aggregates into a **concern band**: `LOW` / `ELEVATED` / `HIGH`.
  Even `LOW` explicitly means "no strong signals," **not** "safe."
- `qr.js` — classifies a decoded QR payload (url / wifi / email / phone / geo /
  otp / vcard / text) and routes URL payloads into the same heuristics.

## REAL vs STUB

**REAL (works now, tested):**
- The entire offline heuristic engine and scoring (21 engine assertions pass).
- The certainty-guardrail report-linter (fails closed).
- Checkout → signed-webhook → session entitlement → gated report generation
  (10 mocked buy-loop tests pass).
- Landing page (`public/index.html`) + delivery UI (`public/success.html`).

**STUB / founder-supplied:**
- **QR image decoding.** Decoding a QR from raw image *pixels* needs a computer-vision
  decoder; that step is client-side (a JS QR library in the browser) or done by any
  scanner the user already has. The engine analyzes the **already-decoded** payload
  string — it never fabricates a decode. Wiring a client-side QR decoder into
  `success.html` is a small, optional enhancement.
- **No live Stripe account / price / keys and no deploy.** The buy-loop tests MOCK
  Stripe and run the entitlement store in-memory. Inert (501) until keys are set.
- **No network reputation feeds.** By design (offline guardrail). There is no
  live redirect-following, WHOIS, or blocklist lookup.

## Buy-loop architecture (mirrors the proven hff-runway pattern)

- `api/create-checkout-session.js` — `$5` one-time Stripe Checkout (`mode:'payment'`).
- `api/webhook.js` — verifies the Stripe signature (fails closed 400), grants a
  one-time entitlement `sess:<checkoutSessionId>` via `lib/store.js`.
- `lib/store.js` — Vercel KV when `KV_REST_API_URL` + `KV_REST_API_TOKEN` are set,
  else an in-memory fallback (used by tests).
- `api/entitlement.js` — `GET ?session_id=` → `{ paid }`.
- `api/generate-report.js` — gated: store entitlement, or a fresh Stripe-verified
  paid session, or `PHISH_DEV_UNLOCK=1` (local only). Fails closed otherwise.

## Tests (run them)

```bash
node test/engine.test.js     # 21 offline-heuristic assertions
node test/buyloop.test.js    # 10 mocked checkout→webhook→entitlement→gate tests
# or:
npm test
```

Both suites pass on Node v22 with **no npm install and no network** (Stripe and
`@vercel/kv` are mocked; the store uses its in-memory fallback).

## Founder go-live steps (the only thing left)

1. Create a **$5 one-time** price in your Stripe account; note the `price_...` id.
2. In Vercel env vars set: `STRIPE_SECRET_KEY`, `STRIPE_PRICE_REPORT`,
   `STRIPE_WEBHOOK_SECRET`, `BASE_URL` (and optionally `KV_REST_API_URL` +
   `KV_REST_API_TOKEN` for a durable entitlement store).
3. Add a Stripe webhook endpoint → `/api/webhook` for `checkout.session.completed`.
4. Deploy via `scripts/factory_deploy.sh` (guard-railed pipeline). Until the keys
   are set the app is inert (checkout + webhook return 501) — no fake green.

*Not affiliated with any brand named in the heuristics; brand tokens are used only
to detect impersonation attempts.*
