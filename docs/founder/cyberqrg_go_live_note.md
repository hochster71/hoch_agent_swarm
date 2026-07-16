# CyberQRG — go-live readiness note

**Product id:** `HCF_CYBERQRG_AI` (Hoch Cyber Factory)
**Status:** SELLABLE-READY (staged) — built, priced, checkout wired. One founder `--go` from live.
**Authored:** 2026-07-16

---

## The product (and why this price)

**CyberQRG Safe-Scan Pack — $9 one-time, 100 QR/link safety scans.**

CyberQRG is an offline-first QR-code / link safety scanner (its engine already
lives in `products/cyberqrg-ai/src` — schemas, security policy, passing tests).
It decodes a QR code or link and scores the destination for phishing / malicious
patterns *before you tap*. Its declared buyer is "everyday users and small teams
who want to know if a QR code / link is safe before tapping."

**Why $9 one-time (not a subscription):**
- It's a **consumer micro-utility** — an impulse-priced safety tool, the class of
  thing people buy once when they need it, not something they'll maintain a
  monthly plan for.
- The engine is **offline-first** — there is no recurring per-user server cost to
  amortize, so a subscription is not justified. One-time fits the cost shape.
- A **"pack of 100 scans"** is a concrete, tangible unit that makes $9 feel fair
  and bounded rather than an open-ended charge.
- $9 sits at a friction-free price point (below the ~$10 "think about it" line),
  maximizing conversion for a first-dollar product.

This can be revised later (e.g. a $19 "pro / unlimited" tier) without changing
the code — tiers are declared in the manifest, not hardcoded.

---

## What is REAL vs STUB

**REAL (built and verified this pass):**
- Deployable web app at `products/cyberqrg-ai/deploy/`:
  - `public/index.html` — landing page that names CyberQRG, shows the **$9 / 100-scan**
    price, lists what it does, and has a working **Buy** button.
  - `public/` also serves `success.html` post-purchase page.
  - `api/create-checkout-session.js` — `POST` endpoint that reads
    `STRIPE_SECRET_KEY` + `STRIPE_PRICE_SCANPACK` from env and returns
    `{ "url": "<stripe url>" }`. Mirrors the proven HSF Story Studio checkout
    (Payment Link first, Checkout Session fallback).
  - `vercel.json`, `package.json` (stripe dep), `.env.example` (placeholders only),
    `.gitignore`.
- **Fail-safe verified:** with no keys the endpoint returns `501 not_configured`
  (proven by a local invocation). It never calls Stripe with a missing/placeholder
  key. The landing page handles the `501` gracefully.
- **Manifest wired:** `coordination/products/products.json` entry for
  `HCF_CYBERQRG_AI` now declares `source_dir`, a `scanpack` price tier ($9
  one-time), `sellable: true`, and rung `3_SELLABLE_READY (staged)`. The
  `factory_to_money.sh` jq logic parses it as exactly 1 sellable tier mapping to
  `STRIPE_PRICE_SCANPACK`.
- The existing TS scanner engine at `products/cyberqrg-ai/src` + tests is
  **untouched**.

**STUB / NOT DONE (founder gate — deliberately):**
- **No Stripe objects** created. No product, no price, no Payment Link. (The `$9`
  Price gets created idempotently at `--go`.)
- **No keys** set anywhere. `STRIPE_SECRET_KEY` / `STRIPE_PRICE_SCANPACK` are
  placeholders in `.env.example`; nothing real is stored or printed.
- **Not deployed.** No Vercel project is confirmed-linked (the manifest lists an
  unconfirmed candidate only). No `vercel deploy` was run.
- The scanner **engine is not yet wired into the landing page** — the page sells
  the pack and takes payment; delivering the actual 100 scans to a buyer
  (entitlement / app hand-off) is the next build increment after first dollar.
  This is a real gap, called out honestly: the checkout loop is complete, the
  post-purchase product delivery is not.

---

## The single command the founder runs to go live

Everything up to the irreversible action is scripted. To go live, from the repo
root on your Mac:

```bash
# 1) READ-ONLY plan first (pastes nothing, deploys nothing, charges nothing):
scripts/factory_to_money.sh HCF_CYBERQRG_AI --plan

# 2) ARM (your click = your authorization). This will:
#    - prompt you ONCE at a hidden native prompt for the live Stripe key
#      (captured into the macOS Keychain, never printed or committed),
#    - validate it directly against api.stripe.com,
#    - idempotently create the $9 "scanpack" Price in THAT key's own account,
#    - set the Vercel prod env vars,
#    - hand off to the guard-railed deploy (preview -> checkout smoke-test ->
#      promote -> auto-rollback on failure).
#    Requires you to be signed in to Vercel.
scripts/factory_to_money.sh HCF_CYBERQRG_AI --go
```

> Note: the task brief referred to this as `scripts/factory_to_money.sh cyberqrg --go`.
> The pipeline matches the **exact** `product_id`, so the working argument is
> `HCF_CYBERQRG_AI` (as shown above), not the short alias.

Before `--go` will succeed you must also confirm/point the manifest at the real
Vercel project for this product (`vercel_project_id` / `vercel_project_name` are
currently `UNKNOWN` — a one-line edit once you pick/confirm the project, so the
source-match guard binds one repo folder to one Vercel project).

**Guard-rails that protect you (doctrine):** default is read-only; the Stripe
secret is only ever in the Keychain + shell memory (never a repo file); a
key/account mismatch aborts before any charge (the Story Studio "No such price"
class of bug); the deploy can only come from `products/cyberqrg-ai/deploy` and
auto-rolls-back if the post-promote checkout smoke-test fails.
