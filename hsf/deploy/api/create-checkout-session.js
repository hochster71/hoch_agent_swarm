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

  const tier = body.tier;

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

    let checkoutUrl;
    try {
      console.log(`[create-checkout-session] Looking for active Payment Link for price ${priceId}...`);
      const paymentLinks = await stripe.paymentLinks.list({ active: true, expand: ['data.line_items'] });
      let paymentLink = paymentLinks.data.find(link => 
        link.line_items && link.line_items.data.some(item => item.price && item.price.id === priceId)
      );

      if (!paymentLink) {
        console.log(`[create-checkout-session] No Payment Link found for price ${priceId}. Creating one...`);
        paymentLink = await stripe.paymentLinks.create({
          line_items: [{ price: priceId, quantity: 1 }],
          metadata: { tier },
        });
      }

      if (paymentLink && paymentLink.url) {
        checkoutUrl = paymentLink.url;
        if (storyId) {
          const separator = checkoutUrl.includes('?') ? '&' : '?';
          checkoutUrl = `${checkoutUrl}${separator}client_reference_id=${encodeURIComponent(storyId)}`;
        }
        console.log('[create-checkout-session] Using Payment Link URL:', checkoutUrl);
      }
    } catch (linkErr) {
      console.error('[create-checkout-session] Payment Link resolution failed, falling back to Checkout Session:', linkErr.message);
    }

    // Fallback to standard Checkout Session if Payment Link could not be resolved/created
    if (!checkoutUrl) {
      const baseUrl =
        process.env.BASE_URL ||
        (req.headers && req.headers.origin) ||
        'https://example.com';

      const session = await stripe.checkout.sessions.create({
        mode: tierConfig.mode,
        line_items: [{ price: priceId, quantity: 1 }],
        success_url: `${baseUrl}/success?session_id={CHECKOUT_SESSION_ID}`,
        cancel_url: `${baseUrl}/?canceled=1`,
        client_reference_id: storyId,
        metadata: { tier, storyId: storyId || '' },
      });
      checkoutUrl = session.url;
      console.log('[create-checkout-session] Using Checkout Session fallback URL:', checkoutUrl);
    }

    // Return the hosted URL as JSON. The client redirects to it.
    return res.status(200).json({ url: checkoutUrl });
  } catch (err) {
    // Never leak internal details / keys. Log server-side, return a generic error.
    console.error('[create-checkout-session] Stripe error:', err && err.message);
    return res.status(502).json({
      error: 'stripe_error',
      message: 'Could not create a checkout session. Please try again later.',
    });
  }
};
