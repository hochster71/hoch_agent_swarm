# HCF — Secret & Key Exposure Scan ($5 one-time)

Paste a config / `.env` / log / code snippet → an **offline heuristic** report of
credential-shaped patterns it contains: vendor key formats (AWS, GitHub, Stripe,
Slack, Google, SendGrid, Twilio), JWTs (only when the header segment REALLY
base64url-decodes to JSON with an `alg`), PEM private-key block markers,
connection-string passwords, and high-entropy values assigned to secret-like
names. Likely placeholders and low-entropy values are set aside and disclosed,
not silently dropped.

**Free preview:** signal counts per severity + concern band only.
**Paid ($5, one Checkout Session = one scan):** every match with line number,
MASKED value, its documented format, and the ordinary benign explanation.

## Guardrails (enforced in code, fail-closed)

- **Heuristic only; never claims certainty.** `engine/report_linter.js` runs on
  every report (paid or free) and withholds the ENTIRE report if any string
  asserts compromise/validity as fact, gives a security directive ("you must…",
  "immediately…"), or gives a safety assurance ("no risk", "you are safe").
  Paying does not buy past the guardrail. A hostile variable name that trips the
  linter yields 422 with no report — fail-closed by design.
- **Masking.** A matched value is never echoed back. Values keep their first 4
  and last 2 characters at most; PEM block contents are never reproduced.
  Covered by tests end-to-end through the paid delivery path.
- **Mandatory disclaimer** ("NOT A GUARANTEE") on every report and preview.

## REAL vs STUB (NO FAKE GREEN)

REAL:
- Deterministic offline engine: vendor-format regexes, JWT header decoding
  (lookalikes whose header is not valid JSON are ignored — tested), PEM
  detection, connection-string password extraction, Shannon-entropy gating,
  placeholder/env-ref suppression with disclosed counts, span-claiming so a
  vendor match is never double-reported by the generic detector.
- Fail-closed report linter + masking guardrail (tested incl. hostile input,
  byte-determinism, CRLF line numbers).
- Full buy loop: Stripe Checkout creator, signature-verified webhook
  (bodyParser disabled, `config` attached AFTER `module.exports = handler` —
  the sibling ordering bug is NOT present here and a regression test pins it),
  session-keyed entitlement store (Vercel KV or in-memory fallback), gated
  `/api/scan`, free `/api/preview`, landing + success UI.

STUB / BY DESIGN:
- **No live Stripe account, price, keys, or deployment.** Every payment path
  returns 501 `not_configured` until the founder sets env vars. Tests MOCK the
  `stripe` module and run the store in-memory — they are NOT a live payment run.
- **Offline by design:** no vendor validation, no breach-database lookup, no
  network calls. A match is a format claim, never proof a credential is real or
  active; a clean result is not proof of absence.
- The vendor-format list is fixed (9 formats) and the generic detector is
  entropy + name heuristics — semantic understanding is out of scope.
- In-memory entitlements do not survive a serverless cold start — configure
  Vercel KV before taking real money.
- `engine/sample/sample_input.txt` is entirely SYNTHETIC (fabricated values in
  documented formats); nothing in this repo is a real credential.

## Founder go-live (the ONLY remaining step)

1. Create a $5 one-time Stripe Price; note the `price_...` id.
2. In Vercel env vars set: `STRIPE_SECRET_KEY`, `STRIPE_PRICE_SCAN`,
   `STRIPE_WEBHOOK_SECRET` (after adding the `/api/webhook` endpoint in the
   Stripe dashboard, event `checkout.session.completed`), `BASE_URL`, and
   Vercel KV (`KV_REST_API_URL`, `KV_REST_API_TOKEN`).
3. Deploy via `scripts/factory_deploy.sh` (guard-railed pipeline only).

Until then the product is inert: free preview works, paid paths return 501.

## Tests

```
npm test   # = node test/engine.test.js && node test/buyloop.test.js
```

No install, no network, no keys required (the `stripe` dependency is only
needed at runtime in production; tests mock it).
