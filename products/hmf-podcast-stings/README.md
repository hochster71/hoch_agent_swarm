# HMF — Podcast Intro & Transition Sting Pack ($9 one-time)

Themed packs of short **instrumental** stings and transitions for podcasters —
intros, outros, bumpers, segment breaks. Buy a pack, download a ZIP containing the
audio, a generated `LICENSE.txt`, and a `manifest.json`. Delivery is **license-gated**.

> **GUARDRAIL (hard):** instrumental-only — **no vocals, no lyrics, no artist- or
> voice-likeness** — enforced by a fail-closed policy gate (`engine/gate.js`). The
> license gate is **mandatory**: nothing is delivered without a paid entitlement.
> **No fabricated audio** ships — the catalog is a placeholder (`available:false`)
> until the founder supplies license-cleared tracks. Shipping placeholder tones as
> a product would be FAKE GREEN.

This reuses the proven **hmf-cue-library store / license-gate** pattern, adapted
to a **$9 one-time, per-pack** purchase.

## What it does (the engine)

- `catalog/catalog.json` + `engine/catalog.js` — the pack catalog (validated,
  fail-closed) with a public preview view that never leaks file paths or bytes.
- `engine/gate.js` — the **policy gate**: rejects any track flagged vocal /
  artist-likeness, any vocal/named-artist text marker, and (in strict mode) any
  missing/empty audio file.
- `engine/entitlements.js` — the **entitlement store** (JSON file; swap for a DB).
  Only the webhook grant path writes entitlements. One-time purchases **accumulate**
  packs per buyer; the gate is per-pack (buying one pack does not unlock another).
- `engine/license.js` — generates `LICENSE.txt` **derived** from the pack's
  structured terms, so the delivered license always matches the catalog of record.
- `engine/packager.js` — runs **both** gates (entitlement, then policy) and only
  then assembles a ZIP. In placeholder mode it ships an honest `README_NO_AUDIO.txt`
  instead of fake audio.
- `engine/zip.js` — a dependency-free PKZIP (DEFLATE + CRC-32) writer.

## REAL vs STUB

**REAL (works now, tested):**
- Catalog load/validate/preview, per-pack license-gate + policy-gate, license
  generation, dependency-free ZIP packaging (9 gate/packaging assertions pass).
- Checkout → signed-webhook → per-pack entitlement → gated ZIP delivery
  (5 mocked webhook tests pass).
- Storefront (`public/store.html`), landing (`index.html`), delivery (`success.html`).

**STUB / founder-supplied (by design, not fake):**
- **No audio.** Every pack is `available:false` and its track files do not exist.
  The founder must drop **license-cleared, instrumental-only** `.wav` files into
  `stings/<pack_id>/` and flip `available:true`. Until then delivery is placeholder
  mode (503 `no_audio_yet` for an entitled buyer of an unavailable pack).
- **No live Stripe account / price / keys and no deploy.** Buy-loop tests MOCK
  Stripe and use a temp JSON store. Inert (501) until keys are set.

## Buy-loop architecture

- `api/create-checkout-session.js` — `$9` one-time (`mode:'payment'`), requires a
  `pack` id, stamps `{ product, tier, pack, subject }` into session metadata.
- `api/webhook.js` — verifies the Stripe signature (fails closed 400); on
  `checkout.session.completed` grants the specific pack via `grantEntitlement`.
  Store path overridable with `STINGS_ENTITLEMENTS_PATH` (tests).
- `api/catalog.js` — public preview catalog (no paid content).
- `api/download.js` — gated: assembles + streams the ZIP only for an entitled
  buyer; 403 if un-entitled, 503 if the pack has no audio yet.

## Tests (run them)

```bash
node test/test_license_gate.js   # 9 license/policy-gate + packaging assertions
node test/test_webhook.js        # 5 mocked webhook→entitlement→delivery tests
# or:
npm test
```

Both pass on Node v22 with **no npm install and no network** (Stripe is mocked;
the entitlement store is a temp JSON file).

## Founder go-live steps (the only things left)

1. Produce/license **instrumental-only** stings (no vocals / no likeness), drop them
   into `stings/<pack_id>/` per the catalog `file` paths, and set that pack
   `"available": true`.
2. Create a **$9 one-time** price in Stripe; note the `price_...` id.
3. In Vercel env vars set: `STRIPE_SECRET_KEY`, `STRIPE_PRICE_STING`,
   `STRIPE_WEBHOOK_SECRET`, `BASE_URL`.
4. Add a Stripe webhook endpoint → `/api/webhook` for `checkout.session.completed`.
5. Deploy via `scripts/factory_deploy.sh`. Inert (501) until keys set — no fake green.
