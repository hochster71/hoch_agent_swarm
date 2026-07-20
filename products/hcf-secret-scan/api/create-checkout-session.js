// api/create-checkout-session.js
//
// HCF — Secret & Key Exposure Scan — Stripe Checkout creator.
//
// One plan:
//   - "scan" -> $5 ONE-TIME payment (mode: 'payment')
//
// SAFETY (mirrors the proven hcf-header-audit shape):
//   * No secrets hardcoded. Keys + price IDs read from env vars.
//   * Missing STRIPE_SECRET_KEY -> 501. INERT until the founder sets keys.
//   * Returns { "url": <hosted checkout url> }.
'use strict';

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'method_not_allowed', message: 'Use POST.' });
  }

  const secretKey = process.env.STRIPE_SECRET_KEY;
  if (!secretKey || secretKey.trim() === '') {
    return res.status(501).json({
      error: 'not_configured',
      message:
        'Payments are not configured. Founder must add STRIPE_SECRET_KEY ' +
        '(and STRIPE_PRICE_SCAN) in Vercel env vars before checkout can work. See README.md.',
    });
  }

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body || '{}'); }
    catch (e) { return res.status(400).json({ error: 'bad_json', message: 'Request body is not valid JSON.' }); }
  }
  body = body || {};

  const tier = body.tier || body.plan || 'scan';
  const TIERS = { scan: { mode: 'payment', priceEnv: 'STRIPE_PRICE_SCAN' } };

  if (!Object.prototype.hasOwnProperty.call(TIERS, tier)) {
    return res.status(400).json({ error: 'invalid_tier', message: "Body must include a valid 'tier'. Allowed: 'scan'." });
  }

  const tierConfig = TIERS[tier];
  const priceId = process.env[tierConfig.priceEnv];
  if (!priceId || priceId.trim() === '') {
    return res.status(501).json({
      error: 'price_not_configured',
      message: `The price ID for tier '${tier}' is not set. Founder must add ${tierConfig.priceEnv} in Vercel env vars. See README.md.`,
    });
  }

  try {
    const Stripe = require('stripe');
    const stripe = new Stripe(secretKey, { apiVersion: '2024-06-20' });
    const baseUrl = process.env.BASE_URL || (req.headers && req.headers.origin) || 'https://example.com';

    const session = await stripe.checkout.sessions.create({
      mode: tierConfig.mode,
      line_items: [{ price: priceId, quantity: 1 }],
      success_url: `${baseUrl}/success.html?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${baseUrl}/?canceled=1`,
      metadata: { product: 'hcf-secret-scan', tier },
    });

    return res.status(200).json({ url: session.url });
  } catch (err) {
    console.error('[create-checkout-session] Stripe error:', err && err.message);
    return res.status(502).json({ error: 'stripe_error', message: 'Could not create a checkout session. Please try again later.' });
  }
};
