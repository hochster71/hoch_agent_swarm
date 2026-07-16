# HMF — HOCH Cue Library

**"Cleared instrumental cues for creators."**

Themed packs of original instrumental music cues — loops, stings, beds, transitions —
license-cleared for video, podcasts, and indie games. Sold as monthly access to a growing library.

- **Price:** $9/mo ($90/yr).
- **Buyer:** video creators, podcasters, indie game devs needing cheap, license-clean background music.
- **Registry:** `coordination/products/product_registry.json` → `HMF_CUE_LIBRARY` (spec: `docs/factories/products/HMF_cue_library.md`).

## Guardrail (honored)

**Instrumental-first, license-cleared, hard policy:**
- No vocals, no lyrics.
- No artist- or voice-likeness of any real person.
- License-gate: every cue ships with an explicit usage license; nothing leaves the factory without
  passing the license gate.

The landing page states all three, and the product ships **no audio** until the license gate is passed
(see `public/cues/PLACEHOLDER.md`).

## What is REAL vs STUB (NO FAKE GREEN)

**REAL (works as written):**
- Deployable static landing page (`public/index.html`) — name, what it is, $9/mo price, working Buy button,
  the instrumental/license guardrail banner, and an honest "audio not attached yet" preview note.
- `POST /api/create-checkout-session` — reads `STRIPE_SECRET_KEY` + `STRIPE_PRICE_MONTHLY` from env and
  returns `{ "url": ... }`, mirroring the proven Story Studio shape. Fails safe with 501 when keys are
  absent (INERT until the founder sets keys).
- `vercel.json`, `.env.example` (placeholders only), success page.

**STUB / NOT BUILT (must not be claimed as done):**
- **There is NO real cue audio.** `public/cues/` contains only a clearly-labeled `PLACEHOLDER.md` — no
  audio files at all. Shipping a placeholder tone as a "product" would be FAKE GREEN, so none is included.
- **No cue-pack producer and no license-gate implementation** exist in this folder. Per the spec, the first
  real pack needs 3 original instrumental files + `LICENSE.txt` + `manifest.json`, passing the license gate
  and an automated no-vocals / no-named-artist check. That producer is remaining work.
- No webhook / entitlement / download-delivery mechanism.

## Remaining work to make it genuinely sellable

1. Produce the first validated, license-clean cue pack (3 instrumental beds + licenses + manifest) and pass
   the license gate + automated no-vocals/no-artist-likeness check (spec acceptance criteria).
2. Build a browse/download library UI + `/api/webhook` → entitlement store gating downloads to subscribers.
3. Founder-gated: create the $9/mo Stripe Price, set env vars, deploy to Vercel.

## Local shape

```
products/hmf-cue-library/
  public/index.html          landing page + Buy button + guardrail banner
  public/success.html        post-checkout thank-you
  public/cues/PLACEHOLDER.md  intentionally NO audio yet (honest stub)
  api/create-checkout-session.js   POST -> { url }
  vercel.json
  .env.example
  package.json
```

Do **not** run `vercel deploy --prod` from here without the guard-railed pipeline. No keys are set;
no Stripe objects are created by this repo.
