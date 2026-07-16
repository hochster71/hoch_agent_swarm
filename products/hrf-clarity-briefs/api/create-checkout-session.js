// api/create-checkout-session.js
//
// HRF — Clarity Briefs — Stripe Checkout Session creator.
//
// Creates a Stripe Checkout Session for one of two options:
//   - "monthly" -> $5/mo recurring subscription (weekly cited briefs)
//   - "brief"   -> $2 one-time single on-demand brief
//
// SAFETY / DESIGN NOTES (mirrors the proven Story Studio shape):
//   * No secrets are hardcoded. All keys and price IDs are read from env vars.
//   * If STRIPE_SECRET_KEY is missing, this FAILS SAFE with a 501 "not
//     configured" response — the scaffold is INERT until the founder adds keys.
//   * Price IDs come from env (STRIPE_PRICE_MONTHLY / STRIPE_PRICE_BRIEF) so
//     the code never assumes a specific Stripe account.
//   * Returns { "url": <hosted checkout url> } — the client redirects to it.

'use strict';

module.exports = async function handler(req, res) {
  // ---- 1. Method guard: only POST ---------------------------------------
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'method_not_allowed', message: 'Use POST.' });
  }

  // ---- 2. Config guard: fail safe if Stripe is not configured -----------
  const secretKey = process.env.STRIPE_SECRET_KEY;
  if (!secretKey || secretKey.trim() === '') {
    return res.status(501).json({
      error: 'not_configured',
      message:
        'Payments are not configured. Founder must add STRIPE_SECRET_KEY ' +
        '(and the price IDs) in Vercel env vars before checkout can work. See README.md.',
    });
  }

  // ---- 3. Parse and validate the request body ---------------------------
  let body = req.body;
  if (typeof body === 'string') {
    try {
      body = JSON.parse(body || '{}');
    } catch (e) {
      return res.status(400).json({ error: 'bad_json', message: 'Request body is not valid JSON.' });
    }
  }
  body = body || {};

  const tier = body.tier || body.plan || 'monthly';

  // mode: 'subscription' for recurring, 'payment' for one-time.
  const TIERS = {
    monthly: { mode: 'subscription', priceEnv: 'STRIPE_PRICE_MONTHLY' },
    brief: { mode: 'payment', priceEnv: 'STRIPE_PRICE_BRIEF' },
  };

  if (!Object.prototype.hasOwnProperty.call(TIERS, tier)) {
    return res.status(400).json({
      error: 'invalid_tier',
      message: "Body must include a valid 'tier'. Allowed values: 'monthly', 'brief'.",
    });
  }

  const tierConfig = TIERS[tier];
  const priceId = process.env[tierConfig.priceEnv];
  if (!priceId || priceId.trim() === '') {
    return res.status(501).json({
      error: 'price_not_configured',
      message:
        `The price ID for tier '${tier}' is not set. Founder must add ` +
        `${tierConfig.priceEnv} in Vercel env vars. See README.md.`,
    });
  }

  // ---- 4. Create the Stripe Checkout Session ----------------------------
  try {
    // Lazy require so the config guards above can run without the package.
    const Stripe = require('stripe');
    const stripe = new Stripe(secretKey, { apiVersion: '2024-06-20' });

    const baseUrl =
      process.env.BASE_URL || (req.headers && req.headers.origin) || 'https://example.com';

    const session = await stripe.checkout.sessions.create({
      mode: tierConfig.mode,
      line_items: [{ price: priceId, quantity: 1 }],
      success_url: `${baseUrl}/success.html?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${baseUrl}/?canceled=1`,
      metadata: { product: 'hrf-clarity-briefs', tier },
    });

    return res.status(200).json({ url: session.url });
  } catch (err) {
    console.error('[create-checkout-session] Stripe error:', err && err.message);
    return res.status(502).json({
      error: 'stripe_error',
      message: 'Could not create a checkout session. Please try again later.',
    });
  }
};
