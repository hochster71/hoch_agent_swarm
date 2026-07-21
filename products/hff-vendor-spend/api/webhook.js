// api/webhook.js
//
// HFF — Vendor Spend Rollup — Stripe webhook (REAL entitlement grant).
//
//   * Verifies the Stripe signature with STRIPE_WEBHOOK_SECRET. FAILS CLOSED
//     (400) on a bad or missing signature.
//   * On `checkout.session.completed`, writes a ONE-TIME entitlement keyed by
//     the Checkout Session id: `sess:<id>` paid:true. That unlocks exactly one
//     paid report for that session.
//
// SAFETY: missing keys -> 501 inert. Raw body required (bodyParser disabled).
// No secrets hardcoded. No money is moved here.
//
// !! ORDERING BUG — KEPT FIXED HERE !!
// Some sibling HFF/HCF products assign `module.exports.config` BEFORE they
// assign `module.exports = handler`, which REPLACES the exports object and
// silently discards `config`. With bodyParser left enabled, Vercel would hand
// the handler a parsed body, the raw bytes would be gone, and EVERY Stripe
// signature verification would fail in production. Here `config` is attached
// AFTER the handler assignment, so it survives. There is a regression test for
// this in test/buyloop.test.js.
'use strict';

function readRawBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on('data', (chunk) => chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk)));
    req.on('end', () => resolve(Buffer.concat(chunks)));
    req.on('error', reject);
  });
}

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'method_not_allowed', message: 'Use POST.' });
  }

  const secretKey = process.env.STRIPE_SECRET_KEY;
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;
  if (!secretKey || !webhookSecret) {
    return res.status(501).json({
      error: 'not_configured',
      message: 'Webhook is not configured. Founder must add STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET in Vercel env vars. See README.md.',
    });
  }

  let event;
  try {
    const Stripe = require('stripe');
    const stripe = new Stripe(secretKey, { apiVersion: '2024-06-20' });
    const rawBody = await readRawBody(req);
    const signature = req.headers['stripe-signature'];
    event = stripe.webhooks.constructEvent(rawBody, signature, webhookSecret);
  } catch (err) {
    console.error('[webhook] Signature verification failed:', err && err.message);
    return res.status(400).json({ error: 'invalid_signature', message: 'Webhook signature verification failed.' });
  }

  try {
    switch (event.type) {
      case 'checkout.session.completed': {
        const session = event.data.object;
        const { setPaid } = require('../lib/store');
        console.log('[webhook] ENTITLEMENT GRANT ->', JSON.stringify({ sessionId: session.id, mode: session.mode }));
        await setPaid('sess:' + session.id, {
          product: 'hff-vendor-spend',
          tier: (session.metadata && session.metadata.tier) || 'report',
          email: (session.customer_details && session.customer_details.email) || null,
        });
        break;
      }
      default:
        console.log('[webhook] unhandled event type:', event.type);
    }
    return res.status(200).json({ received: true });
  } catch (err) {
    console.error('[webhook] handler error:', err && err.message);
    return res.status(500).json({ error: 'handler_error', message: 'Failed to process event.' });
  }
};

// MUST stay AFTER the assignment above — see the note in the file header.
module.exports.config = { api: { bodyParser: false } };
