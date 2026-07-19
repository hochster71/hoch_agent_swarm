// api/create-checkout-session.js
//
// Hoch Storybook Factory (HSF) — Stripe Checkout Session creator.
//
// Creates a Stripe Checkout Session for one of two products:
//   - "onestory"  -> $19 one-time, single-story export
//   - "creators"  -> $12/mo recurring subscription
//
// SAFETY / DESIGN NOTES:
//   * No secrets are hardcoded. All keys and price IDs are read from env vars.
//   * If STRIPE_SECRET_KEY is missing, this function FAILS SAFE with a 501
//     "not configured" response instead of attempting a broken Stripe call.
//     This means the scaffold is INERT until the founder adds real keys.
//   * Price IDs are read from env (STRIPE_PRICE_ONESTORY / STRIPE_PRICE_CREATORS)
//     so the code never assumes a specific Stripe account.
//
// Runtime: Node.js serverless function (CommonJS). Requires the `stripe`
// package at deploy time (see package.json note in README). Because the
// require is done lazily inside the handler, the missing-key guard can run
// even if `stripe` is not installed yet.

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
  // This is the "inert until keys added" behaviour. We NEVER call Stripe
  // with a missing/placeholder key — we return a clear 501 instead.
  const secretKey = process.env.STRIPE_SECRET_KEY;
  if (!secretKey || secretKey.trim() === '') {
    return res.status(501).json({
      error: 'not_configured',
      message:
        'Payments are not configured. Founder must add STRIPE_SECRET_KEY ' +
        '(and the price IDs) in Vercel env vars before checkout can work. ' +
        'See hsf/deploy/README.md.',
    });
  }

  // ---- 3. Parse and validate the request body ---------------------------
  // Vercel usually parses JSON bodies automatically, but we defensively
  // handle a raw string body too.
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

  const tier = body.tier || body.product;

  // Map each supported tier to its Stripe config.
  // `mode` is required by Stripe: 'payment' for one-time, 'subscription' for recurring.
  const TIERS = {
    onestory: {
      mode: 'payment',
      priceEnv: 'STRIPE_PRICE_ONESTORY',
    },
    creators: {
      mode: 'subscription',
      priceEnv: 'STRIPE_PRICE_CREATORS',
    },
  };

  if (!tier || !Object.prototype.hasOwnProperty.call(TIERS, tier)) {
    return res.status(400).json({
      error: 'invalid_tier',
      message:
        "Body must include a valid 'tier'. Allowed values: 'onestory', 'creators'.",
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
        `${tierConfig.priceEnv} in Vercel env vars. See hsf/deploy/README.md.`,
    });
  }

  // ---- 4. Resolve the Stripe Payment Link (fallback to Checkout Session) --
  try {
    // Lazy require so the config guards above can run without the package.
    // eslint-disable-next-line global-require
    const Stripe = require('stripe');
    const stripe = new Stripe(secretKey, { apiVersion: '2024-06-20' });

    // storyId ties a onestory purchase to the specific story the webhook must unlock.
    const storyId = body.storyId ? String(body.storyId).slice(0, 64) : undefined;

    // Canonical hosted Checkout Session. (The previous Payment-Link detour passed an
    // invalid `expand: ['data.line_items']` to paymentLinks.list, which throws on every
    // call and collapsed into the fallback — masking the real error. Removed.)
    //
    // Auto-detect the price's mode so we never mismatch 'payment' vs 'subscription':
    // passing mode:'payment' with a recurring price (or vice-versa) is the most common
    // cause of a create failure. We read the price and let it decide.
    let mode = tierConfig.mode;
    try {
      const priceObj = await stripe.prices.retrieve(priceId);
      mode = priceObj && priceObj.recurring ? 'subscription' : 'payment';
    } catch (pe) {
      console.error('[create-checkout-session] price.retrieve failed, using configured mode:', pe && pe.message);
    }

    const baseUrl =
      (process.env.BASE_URL && /^https?:\/\//.test(process.env.BASE_URL) ? process.env.BASE_URL : null) ||
      (req.headers && req.headers.origin) ||
      'https://story-studio-live.vercel.app';

    const session = await stripe.checkout.sessions.create({
      mode,
      line_items: [{ price: priceId, quantity: 1 }],
      success_url: `${baseUrl}/success?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${baseUrl}/?canceled=1`,
      client_reference_id: storyId,
      metadata: { tier, storyId: storyId || '' },
    });
    const checkoutUrl = session.url;
    console.log('[create-checkout-session] Checkout Session created:', session.id, 'mode:', mode);

    // Return the hosted URL as JSON. The client redirects to it.
    return res.status(200).json({ url: checkoutUrl });
  } catch (err) {
    // Never leak internal details / keys. Log server-side, return a generic error.
    console.error('[create-checkout-session] Stripe error:', err && err.message);
    // Safe diagnostics: Stripe error type/code/param/message never contain the secret
    // key. Surfacing them turns an opaque failure into a precise, fixable cause.
    return res.status(502).json({
      error: 'stripe_error',
      message: 'Could not create a checkout session.',
      stripe_type: (err && err.type) || null,
      stripe_code: (err && err.code) || null,
      stripe_param: (err && err.param) || null,
      detail: (err && err.message) || null,
    });
  }
};
