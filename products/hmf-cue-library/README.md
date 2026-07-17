# HMF — HOCH Cue Library

**"Cleared instrumental cues for creators."**

Themed packs of original instrumental music cues — loops, stings, beds, transitions —
license-cleared for video, podcasts, and indie games. Sold as monthly access to a growing library.

- **Price:** $9/mo ($90/yr).
- **Buyer:** video creators, podcasters, indie game devs needing cheap, license-clean background music.
- **Registry:** `coordination/products/product_registry.json` → `HMF_CUE_LIBRARY`
  (spec: `docs/factories/products/HMF_cue_library_engine_spec.md`).

## Guardrail (HARD, enforced in code)

**Instrumental-first, license-cleared:**
- No vocals, no lyrics.
- No artist- or voice-likeness of any real person.
- **License gate is mandatory** — every cue ships with an explicit usage license, and delivery only
  happens after (1) an active entitlement AND (2) a per-file policy check. Nothing leaves the factory
  without passing both. Fail-closed.

The policy check (`engine/gate.js`) rejects any track flagged `vocals`/`artist_likeness`, any
"in the style of <named artist>" / vocal text markers, and (in strict mode) missing/empty files.

## What is REAL vs STUB (NO FAKE GREEN)

**REAL — store / gate / packaging engine (all tested):**
- **Catalog data model** — `catalog/catalog.json` drives everything (pack id, title, mood/tempo/genre
  tags, per-track metadata, per-pack license terms). Loaded + validated fail-closed by `engine/catalog.js`.
- **License gate / entitlement store** — `engine/entitlements.js`. Only a (webhook) grant path writes
  entitlements; `isEntitled(subject, pack)` is the gate. Un-entitled users are denied delivery.
- **Policy gate** — `engine/gate.js`. Per-file instrumental / no-artist-likeness check, fail-closed.
- **Packaging + delivery** — `engine/packager.js` assembles a purchased pack as a ZIP (pure-JS writer
  `engine/zip.js`, no deps) containing the tracks + a `LICENSE.txt` **generated from the pack's license
  terms** + a `manifest.json`. Both gates run before any bytes are assembled.
- **Storefront listing UI** — `public/store.html` renders the catalog from `GET /api/catalog`
  (metadata + previews only; no file paths or audio exposed to un-entitled visitors).
- **Delivery endpoint** — `GET /api/download?pack=<id>` → `403 not_entitled` for non-buyers,
  streams the ZIP for entitled buyers, `503 no_audio_yet` while audio is absent (by design).
- **Checkout** — `POST /api/create-checkout-session` (unchanged) reads `STRIPE_SECRET_KEY` +
  `STRIPE_PRICE_MONTHLY` from env; fails safe 501 when unset (INERT until keys).
- **Test** — `npm test` (`test/test_license_gate.js`): proves the gate blocks un-entitled delivery,
  allows entitled delivery, generates the license from terms, and **fails closed on a seeded
  vocal-containing track**. Result: **7 passed, 0 failed**.

**STUB / NOT BUILT (must not be claimed as done):**
- **There is NO real cue audio.** `catalog/catalog.json` is a clearly-labeled `"status":"PLACEHOLDER"`
  manifest; every pack is `"available": false` and references track files that DO NOT EXIST. `cues/`
  contains only `PLACEHOLDER.md`. Shipping placeholder tones would be FAKE GREEN, so none is included.
- **No Stripe webhook wired** — the entitlement store exists and is the delivery gate, but the
  `checkout.session.completed` → `grantEntitlement()` webhook and the buyer-identity/session layer
  (`x-hmf-subject` resolution in `api/download.js`) are stubbed for the founder to connect to real auth.

## Founder steps to go LIVE (exact)

1. **Supply cleared audio.** For each pack in `catalog/catalog.json`, drop license-cleared,
   **instrumental-only** tracks into `cues/<pack_id>/` matching the manifest `file` names
   (see `cues/PLACEHOLDER.md`). You must hold redistribution/sublicense-clean rights.
2. **Flip availability.** Set each ready pack's `"available": true` (and the catalog `"status": "LIVE"`).
   Run `npm test` and a strict assemble (`requireAudio=true`) — the policy gate blocks any pack with a
   missing/empty file or a vocal/likeness flag.
3. **Wire entitlement.** Add `/api/webhook` (`checkout.session.completed` → `grantEntitlement(customerId)`)
   and resolve the buyer identity in `api/download.js` from your real session, not request input.
4. **Stripe + deploy (founder-gated).** Create the $9/mo Price, set `STRIPE_SECRET_KEY` /
   `STRIPE_PRICE_MONTHLY` in Vercel env, and ship via the guard-railed pipeline
   (`scripts/factory_deploy.sh`) — **not** `vercel deploy --prod` from here.

## What remains to be genuinely sellable

1. Real, license-cleared instrumental audio for ≥1 pack (the founder-supplied dependency).
2. Stripe webhook + auth wiring so entitlements are granted by real purchases.
3. Founder-gated: Stripe Price, env vars, guard-railed deploy.

Everything ELSE — catalog model, license gate, policy gate, packaging, delivery, storefront, tests — is
built and passing.

## Local shape

```
products/hmf-cue-library/
  catalog/catalog.json              PLACEHOLDER catalog manifest (packs, tags, tracks, license terms)
  engine/catalog.js                 load/validate + public (preview) vs full views
  engine/entitlements.js            entitlement store — the purchase gate
  engine/gate.js                    per-file instrumental / no-likeness policy gate
  engine/license.js                 renders LICENSE.txt from pack terms
  engine/zip.js                     dependency-free ZIP writer
  engine/packager.js                gated pack assembly (both gates -> ZIP)
  api/catalog.js                    GET /api/catalog — metadata/previews only
  api/download.js                   GET /api/download?pack=<id> — gated ZIP delivery
  api/create-checkout-session.js    POST -> { url } (Stripe, fails safe 501)
  public/index.html                 landing page + Buy button + guardrail banner
  public/store.html                 storefront listing UI (reads /api/catalog)
  public/success.html               post-checkout thank-you
  cues/PLACEHOLDER.md               founder drops cleared audio here (NO audio shipped)
  test/test_license_gate.js         npm test — gate + packaging proof (7 passing)
  vercel.json  package.json  .env.example
```

Do **not** run `vercel deploy --prod` from here without the guard-railed pipeline. No keys are set;
no Stripe objects are created by this repo; no real audio ships.
