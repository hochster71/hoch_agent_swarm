// api/webhook.js
//
// HFF — Invoice Aging — Stripe webhook handler (REAL entitlement grant).
//
// Responsibilities:
//   * Verify the Stripe signature using STRIPE_WEBHOOK_SECRET. FAILS CLOSED (400)
//     on a bad/missing signature.
//   * On `checkout.session.completed`, write a one-time entitlement to the store
//     (lib/store.js), keyed by the checkout SESSION id. That unlocks (re)download
//     of the report bought in that session.
//
// SAFETY / DESIGN NOTES (mirrors the proven hff-runway / hsf webhook):
//   * FAILS SAFE: if STRIPE_SECRET_KEY or STRIPE_WEBHOOK_SECRET is missing, return
//     501 "not configured" and process nothing — inert until keys added.
//   * Requires the RAW request body to verify the signature (bodyParser disabled).
//   * No secrets hardcoded. No money moved here.

'use strict';

module.exports.config = { api: { bodyParser: false } };

function readRawBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on('data', (chunk) => chunks.push(chunk));
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
      message:
        'Webhook is not configured. Founder must add STRIPE_SECRET_KEY and ' +
        'STRIPE_WEBHOOK_SECRET in Vercel env vars. See README.md.',
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
        console.log('[webhook] ENTITLEMENT GRANT ->', JSON.stringify({ sessionId: session.id, mode: session.mode }));
        const { setPaid } = require('../lib/store');
        if (session.id) {
          await setPaid('sess:' + session.id, {
            tier: 'report',
            product: 'hff-invoice-aging',
            email: (session.customer_details && session.customer_details.email) || null,
          });
        }
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
