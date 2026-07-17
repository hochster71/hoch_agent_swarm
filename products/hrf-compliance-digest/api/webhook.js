// api/webhook.js
//
// HRF — Compliance Change Digest — Stripe webhook handler (REAL entitlement grant).
// Mirrors the proven hff-runway subscription webhook.
//
//   * Verify the Stripe signature (STRIPE_WEBHOOK_SECRET). FAILS CLOSED (400).
//   * checkout.session.completed  -> setPaid('email:<addr>') + cust:<id>->email map.
//   * customer.subscription.deleted -> revoke by customer id.
//   * customer.subscription.updated -> re-grant/revoke on status.
//   * FAILS SAFE (501) until STRIPE_SECRET_KEY + STRIPE_WEBHOOK_SECRET set.

'use strict';

module.exports.config = { api: { bodyParser: false } };

function readRawBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on('data', (c) => chunks.push(Buffer.isBuffer(c) ? c : Buffer.from(c)));
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
    return res.status(501).json({ error: 'not_configured', message: 'Webhook is not configured. Founder must add STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET in Vercel env vars. See README.md.' });
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
        const email = (session.customer_details && session.customer_details.email) || session.customer_email || null;
        const { setPaid, put } = require('../lib/store');
        console.log('[webhook] ENTITLEMENT GRANT ->', JSON.stringify({ email, sessionId: session.id, mode: session.mode }));
        if (email) {
          await setPaid('email:' + email.toLowerCase(), { tier: 'monthly', product: 'hrf-compliance-digest', sessionId: session.id });
          if (session.customer) await put('cust:' + session.customer, { email });
        }
        break;
      }
      case 'customer.subscription.deleted': {
        const sub = event.data.object;
        const { setUnpaid, get } = require('../lib/store');
        const m = sub.customer ? await get('cust:' + sub.customer) : null;
        if (m && m.email) await setUnpaid('email:' + m.email.toLowerCase());
        console.log('[webhook] revoked subscription for', m && m.email);
        break;
      }
      case 'customer.subscription.updated': {
        const sub = event.data.object;
        const { setPaid, setUnpaid, get } = require('../lib/store');
        const m = sub.customer ? await get('cust:' + sub.customer) : null;
        if (m && m.email) {
          if (sub.status === 'active' || sub.status === 'trialing') await setPaid('email:' + m.email.toLowerCase(), { tier: 'monthly', product: 'hrf-compliance-digest', via: 'sub.updated' });
          else await setUnpaid('email:' + m.email.toLowerCase());
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
