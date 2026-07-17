// api/webhook.js
//
// HMF — Podcast Sting Pack — Stripe webhook handler (REAL). It is the ONLY thing
// that grants an entitlement. Flow:
//
//   create-checkout-session.js -> starts a paid Stripe Checkout Session and
//                                 stamps { product, tier, pack, subject } into
//                                 the session metadata.
//   Stripe                     -> on payment, POSTs `checkout.session.completed`
//                                 here with a signed body.
//   THIS FILE                  -> verifies the signature, resolves the buyer +
//                                 the purchased pack, and calls grantEntitlement()
//                                 so isEntitled() then passes and api/download.js
//                                 can serve the ZIP.
//
// SAFETY (mirrors proven cue-library / hsf webhook):
//   * FAILS SAFE: missing STRIPE_SECRET_KEY / STRIPE_WEBHOOK_SECRET -> 501, inert.
//   * FAILS CLOSED on a bad/forged signature -> 400, no entitlement written.
//   * Raw body required for verification (bodyParser disabled).
//   * Store path overridable via STINGS_ENTITLEMENTS_PATH (tests).

'use strict';

const { grantEntitlement, revokeEntitlement } = require('../engine/entitlements');

module.exports.config = { api: { bodyParser: false } };

function readRawBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on('data', (chunk) => chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk)));
    req.on('end', () => resolve(Buffer.concat(chunks)));
    req.on('error', reject);
  });
}

function storePath() {
  const p = process.env.STINGS_ENTITLEMENTS_PATH;
  return p && p.trim() !== '' ? p : undefined;
}

function resolveSubject(session) {
  const meta = session.metadata || {};
  const email = session.customer_details && session.customer_details.email;
  return (
    (meta.subject && String(meta.subject)) ||
    (email && String(email).toLowerCase()) ||
    (session.customer && String(session.customer)) ||
    (session.client_reference_id && String(session.client_reference_id)) ||
    null
  );
}

// A specific pack id in metadata grants just that pack (one-time purchase). If no
// pack was stamped (shouldn't happen for this product), grant nothing specific.
function resolvePacks(session) {
  const meta = session.metadata || {};
  const pack = meta.pack || meta.packId || meta.pack_id;
  if (pack && String(pack).trim() !== '') return [String(pack)];
  return [];
}

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'method_not_allowed', message: 'Use POST.' });
  }

  const secretKey = process.env.STRIPE_SECRET_KEY;
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;
  if (!secretKey || !webhookSecret) {
    return res.status(501).json({ error: 'not_configured', message: 'Webhook is not configured. Founder must add STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET in Vercel env vars before purchases can grant access. See README.md.' });
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
        const session = event.data.object || {};
        const subject = resolveSubject(session);
        const packs = resolvePacks(session);

        if (!subject) {
          console.error('[webhook] checkout.session.completed with NO resolvable subject', { sessionId: session.id });
          break;
        }
        if (!packs.length) {
          console.error('[webhook] checkout.session.completed with NO pack in metadata', { sessionId: session.id, subject });
          break;
        }

        const record = grantEntitlement(subject, {
          packs,
          source: 'stripe_webhook',
          session_id: session.id,
          email: (session.customer_details && session.customer_details.email) || null,
          customer: session.customer || null,
        }, storePath());

        // Also key by the Stripe customer id when present + distinct.
        if (session.customer && String(session.customer) !== subject) {
          grantEntitlement(String(session.customer), { packs, source: 'stripe_webhook', session_id: session.id }, storePath());
        }

        console.log('[webhook] ENTITLEMENT GRANT ->', JSON.stringify({ subject, packs: record.packs, sessionId: session.id }));
        break;
      }

      case 'charge.refunded': {
        // Optional: revoke on refund keyed by customer id.
        const charge = event.data.object || {};
        if (charge.customer) {
          revokeEntitlement(String(charge.customer), storePath());
          console.log('[webhook] revoked entitlement for refunded customer', charge.customer);
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
