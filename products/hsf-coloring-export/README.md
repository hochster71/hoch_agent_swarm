# HSF — Coloring Book Export

Turn a Story Studio story into a printable **line-art coloring book PDF**: a cover,
one big vector drawing per scene with an outlined (colorable) heading and a
read-aloud caption, and a "colored by" certificate back page. The free preview is
**always watermarked**; a **$7 one-time** purchase unlocks the watermark-free
export for that story session.

Part of the HELM autonomous factory line (HSF — Hoch Storybook Factory). Built to
CODE-COMPLETE on 2026-07-17. **$0 earned; nothing is deployed; checkout is inert
until the founder adds keys.**

## How it works

```
public/app.html  --story spec-->  POST /api/export-coloring-book
                                    |-- child-safety gate (fail-closed)
                                    |-- watermarked preview  (free, always)
                                    '-- watermark-free PDF   (only if entitled)

Buy $7 --> POST /api/create-checkout-session --> Stripe Checkout
       --> Stripe fires checkout.session.completed --> POST /api/webhook
           (signature verified, fail-closed) --> lib/store.js sess:<id> paid:true
       --> success.html reattaches session_id --> watermark-free export unlocked
```

- **Engine** (`engine/`): vendored copy of the live Story Studio engine
  (`story-engine.js`) normalizes a spec into the same 8–10 scene arc the studio
  shows; `motifs.js` picks a deterministic kid-friendly vector drawing per scene
  (sun, sailboat, rocket, butterfly, …); `render_pdf.js` writes a dependency-free
  multi-page PDF 1.4 with stroke-only paths and outline-mode text; `safety.js` is
  the child-safety gate.
- **Watermark guardrail**: the engine defaults to watermarked; only
  `watermarkFree === true` (strict boolean, set solely by the entitlement-gated
  endpoint) strips it. Tests assert truthy-but-not-true values stay watermarked.
- **Child-safety guardrail**: every string that reaches the page (title, kickers,
  headings, bodies, chips) passes a fail-closed blocklist gate (violence, weapons,
  adult content, drugs/alcohol, profanity, self-harm, hate). One hit refuses the
  whole export with `SAFETY_GATE_FAILED` — **paid or not**.
- **Entitlements** (`lib/store.js`): `@vercel/kv` when `KV_REST_API_URL` +
  `KV_REST_API_TOKEN` are set, in-memory fallback otherwise. Keyed
  `sess:<checkout_session_id>` so a buyer can re-export their purchase.

## REAL vs STUB (honest inventory)

**REAL and tested:**
- Story normalization (spec path through the vendored story engine, and direct
  Story Studio `scenes` path), scene cap at 12, fail-closed empty/garbage input rejection.
- Child-safety gate (fail-closed; scans title + all scene text; applies to paid exports too).
- Deterministic vector line-art motifs and multi-page PDF renderer (valid PDF 1.4
  envelope, correct page counts, identical bytes for identical input, escaping
  hardened against hostile story text).
- Watermark on every page in preview mode; stripped only behind the entitlement gate.
- Checkout-session endpoint, signature-verified fail-closed webhook (400 bad
  signature, 501 inert without keys), entitlement store + route, gated delivery
  endpoint, landing + studio + success UI.

**STUB / by design, not yet real:**
- **No live Stripe account/price/keys and no deploy** — checkout and webhook return
  501 until the founder configures env vars. $0 has been earned.
- Buy-loop tests **mock** the `stripe` module and run the store **in-memory**; they
  prove code-path coherence, not a live Stripe run.
- Line-art is generated from a fixed motif library keyed to the story arc — it is
  real vector art, but it is **not** an illustration of the user's specific text
  (no image model; deterministic by design).
- The safety gate is a deterministic keyword filter, not a semantic classifier.
- The in-browser Story Studio app itself lives at `hsf/story-studio-v2.html`; this
  product embeds a minimal spec form rather than the full studio UI.

## Tests

```
cd products/hsf-coloring-export
npm test        # = node test/engine.test.js && node test/buyloop.test.js
```

No install, no network needed (node v18+; verified on v22): 14 engine tests +
11 buy-loop tests.

## Founder go-live steps (the only remaining gate)

1. In Stripe: create a **$7 one-time** price for "Coloring Book Export"; copy the
   `price_...` id. Add a webhook endpoint `<BASE_URL>/api/webhook` for
   `checkout.session.completed`; copy the `whsec_...` secret.
2. In Vercel project env vars set: `STRIPE_SECRET_KEY`, `STRIPE_PRICE_EXPORT`,
   `STRIPE_WEBHOOK_SECRET`, `BASE_URL` (and optionally `KV_REST_API_URL` +
   `KV_REST_API_TOKEN` for durable entitlements).
3. Deploy via the guard-railed pipeline only: `scripts/factory_deploy.sh`
   (never a raw `vercel --prod`). Until step 2, every paid path returns 501 and
   the product is inert — the free watermarked preview works regardless.
