// api/create-checkout-session.js
//
// HMF — HOCH Cue Library — Stripe Checkout Session creator.
//
// One plan:
//   - "monthly" -> $9/mo recurring subscription (access to the cue library)
//
// SAFETY / DESIGN NOTES (mirrors the proven Story Studio shape):
//   * No secrets hardcoded. Keys + price IDs read from env vars.
//   * If STRIPE_SECRET_KEY is missing, FAILS SAFE with a 501 — INERT until keys.
//   * Price ID from env (STRIPE_PRICE_MONTHLY) — never assumes a Stripe account.
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
        '(and STRIPE_PRICE_MONTHLY) in Vercel env vars before checkout can work. See README.md.',
    });
  }

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
  const TIERS = {
    monthly: { mode: 'subscription', priceEnv: 'STRIPE_PRICE_MONTHLY' },
  };

  if (!Object.prototype.hasOwnProperty.call(TIERS, tier)) {
    return res.status(400).json({
      error: 'invalid_tier',
      message: "Body must include a valid 'tier'. Allowed values: 'monthly'.",
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

  // Optional purchase details the WEBHOOK will read back to grant access:
  //   * pack    -> entitle only that pack id (omit for full-library subscription)
  //   * subject -> stable buyer id the delivery gate keys on (e.g. an app user id);
  //                if omitted, the webhook falls back to the customer email.
  // Both are clamped and stamped into the session metadata / client_reference_id.
  const pack = body.pack ? String(body.pack).slice(0, 64) : '';
  const subject = body.subject ? String(body.subject).slice(0, 128) : '';

  try {
    const Stripe = require('stripe');
    const stripe = new Stripe(secretKey, { apiVersion: '2024-06-20' });

    const baseUrl =
      process.env.BASE_URL || (req.headers && req.headers.origin) || 'https://example.com';

    const session = await stripe.checkout.sessions.create({
      mode: tierConfig.mode,
      line_items: [{ price: priceId, quantity: 1 }],
      success_url: `${baseUrl}/success.html?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${baseUrl}/?canceled=1`,
      // client_reference_id mirrors subject so the webhook can recover identity
      // even if metadata is stripped by an intermediary.
      client_reference_id: subject || undefined,
      // The webhook (api/webhook.js) reads pack + subject to call grantEntitlement.
      metadata: { product: 'hmf-cue-library', tier, pack, subject },
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
