// api/create-checkout-session.js
//
// CyberQRG (Hoch Cyber Factory / HCF) — Stripe Checkout Session creator.
//
// Sells ONE product:
//   - "scanpack" -> $9 one-time, a pack of 100 QR/link safety scans.
//
// SAFETY / DESIGN NOTES (mirrors the proven HSF Story Studio checkout):
//   * No secrets are hardcoded. All keys and price IDs are read from env vars.
//   * If STRIPE_SECRET_KEY is missing, this function FAILS SAFE with a 501
//     "not configured" response instead of attempting a broken Stripe call.
//     The scaffold is INERT until the founder adds real keys in Vercel.
//   * The price ID is read from env (STRIPE_PRICE_SCANPACK) so the code never
//     assumes a specific Stripe account.
//   * Prefers a Stripe Payment Link (auto-created for the price if none exists),
//     falling back to a Checkout Session. Always returns { "url": "..." }.
//
// Runtime: Node.js serverless function (CommonJS). Requires the `stripe`
// package at deploy time. The require is lazy so the missing-key guard can
// run even before `stripe` is installed.

'use strict';

module.exports = async function handler(req, res) {
  // ---- 1. Method guard: only POST is allowed ----------------------------
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res
      .status(405)
      .json({ error: 'method_not_allowed', message: 'Use POST.' });
  }

  // ---- 2. Config guard: fail safe if Stripe is not configured -----------
  const secretKey = process.env.STRIPE_SECRET_KEY;
  if (!secretKey || secretKey.trim() === '') {
    return res.status(501).json({
      error: 'not_configured',
      message:
        'Payments are not configured. Founder must add STRIPE_SECRET_KEY ' +
        '(and STRIPE_PRICE_SCANPACK) in Vercel env vars before checkout can ' +
        'work. See README.md.',
    });
  }

  // ---- 3. Parse and validate the request body ---------------------------
  let body = req.body;
  if (typeof body === 'string') {
    try {
      body = JSON.parse(body || '{}');
    } catch (e) {
      return res
        .status(400)
        .json({ error: 'bad_json', message: 'Request body is not valid JSON.' });
    }
  }
  body = body || {};

  const tier = body.tier || 'scanpack';

  // Map each supported tier to its Stripe config.
  const TIERS = {
    scanpack: {
      mode: 'payment', // one-time
      priceEnv: 'STRIPE_PRICE_SCANPACK',
    },
  };

  if (!Object.prototype.hasOwnProperty.call(TIERS, tier)) {
    return res.status(400).json({
      error: 'invalid_tier',
      message: "Body 'tier' must be 'scanpack'.",
    });
  }

  const tierConfig = TIERS[tier];
  const priceId = process.env[tierConfig.priceEnv];

  // Guard: the tier is valid but its price ID env var was never set.
  if (!priceId || priceId.trim() === '') {
    return res.status(501).json({
      error: 'price_not_configured',
      message:
        `The price ID for tier '${tier}' is not set. Founder must add ` +
        `${tierConfig.priceEnv} in Vercel env vars. See README.md.`,
    });
  }

  // ---- 4. Resolve a Stripe Payment Link (fallback to Checkout Session) ---
  try {
    // Lazy require so the config guards above can run without the package.
    // eslint-disable-next-line global-require
    const Stripe = require('stripe');
    const stripe = new Stripe(secretKey, { apiVersion: '2024-06-20' });

    let checkoutUrl;
    try {
      const paymentLinks = await stripe.paymentLinks.list({
        active: true,
        expand: ['data.line_items'],
      });
      let paymentLink = paymentLinks.data.find(
        (link) =>
          link.line_items &&
          link.line_items.data.some(
            (item) => item.price && item.price.id === priceId
          )
      );

      if (!paymentLink) {
        paymentLink = await stripe.paymentLinks.create({
          line_items: [{ price: priceId, quantity: 1 }],
          metadata: { tier },
        });
      }

      if (paymentLink && paymentLink.url) {
        checkoutUrl = paymentLink.url;
      }
    } catch (linkErr) {
      console.error(
        '[create-checkout-session] Payment Link resolution failed, falling back to Checkout Session:',
        linkErr.message
      );
    }

    // Fallback to a standard Checkout Session if the Payment Link failed.
    if (!checkoutUrl) {
      const baseUrl =
        process.env.BASE_URL ||
        (req.headers && req.headers.origin) ||
        'https://example.com';

      const session = await stripe.checkout.sessions.create({
        mode: tierConfig.mode,
        line_items: [{ price: priceId, quantity: 1 }],
        success_url: `${baseUrl}/success.html?session_id={CHECKOUT_SESSION_ID}`,
        cancel_url: `${baseUrl}/?canceled=1`,
        metadata: { tier },
      });
      checkoutUrl = session.url;
    }

    return res.status(200).json({ url: checkoutUrl });
  } catch (err) {
    // Never leak internal details / keys. Log server-side, return generic.
    console.error('[create-checkout-session] Stripe error:', err && err.message);
    return res.status(502).json({
      error: 'stripe_error',
      message: 'Could not create a checkout session. Please try again later.',
    });
  }
};
