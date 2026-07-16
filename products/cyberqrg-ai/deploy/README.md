# CyberQRG — deploy bundle

Minimal deployable web app for **CyberQRG**, the offline-first QR / link safety
scanner (Hoch Cyber Factory, HCF). Static landing page + one Stripe checkout
serverless function. Mirrors the proven HSF Story Studio checkout shape.

## What sells

- **CyberQRG Safe-Scan Pack** — **$9 one-time**, a pack of **100 QR/link safety scans**.

## Structure

```
deploy/
  public/index.html          landing page: names product, shows $9 price, Buy button
  public/... (success.html)  post-purchase page (served at /success.html)
  api/create-checkout-session.js   POST endpoint -> { "url": "<stripe url>" }
  vercel.json                Vercel config (serverless api/, no-store on /api)
  package.json               stripe dependency
  .env.example               placeholder env (NO real keys)
```

## Fail-safe behaviour

The checkout endpoint is **inert until the founder adds keys**:

- No `STRIPE_SECRET_KEY`  -> `501 not_configured`
- No `STRIPE_PRICE_SCANPACK` -> `501 price_not_configured`

It never calls Stripe with a missing/placeholder key. The landing page handles
the `501` gracefully ("Checkout goes live once the founder adds Stripe keys").

## Going live (founder gate — NOT done here)

1. In Stripe: create a **$9 one-time** Price named "CyberQRG Safe-Scan Pack —
   100 scans". Copy its `price_...` id.
2. In Vercel (this project's env vars): set `STRIPE_SECRET_KEY`,
   `STRIPE_PRICE_SCANPACK`, and `BASE_URL`.
3. Deploy through the guard-railed pipeline (see
   `docs/founder/cyberqrg_go_live_note.md`).

No secrets live in this repo. Everything above is the founder's click.
