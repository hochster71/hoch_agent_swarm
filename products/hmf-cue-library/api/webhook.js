// api/webhook.js
//
// HMF Cue Library — Stripe webhook handler (REAL).
//
// This is the write-side of the PURCHASE -> ACCESS path. It is the ONLY thing
// that grants an entitlement. Flow:
//
//   create-checkout-session.js  -> starts a paid Stripe Checkout Session and
//                                  stamps { product, tier, pack, subject } into
//                                  the session metadata.
//   Stripe                      -> on payment, POSTs `checkout.session.completed`
//                                  here with a signed body.
//   THIS FILE                   -> verifies the signature, resolves the buyer +
//                                  the purchased pack, and calls the engine's
//                                  grantEntitlement() so isEntitled() then passes
//                                  and api/download.js can serve the ZIP.
//
// SAFETY / DESIGN NOTES (mirrors the proven Story Studio / HSF webhook):
//   * FAILS SAFE: if STRIPE_SECRET_KEY or STRIPE_WEBHOOK_SECRET is missing, we
//     return 501 "not configured" and grant NOTHING. Inert until keys added.
//   * FAILS CLOSED on a bad/forged signature -> 400, no entitlement written.
//   * Requires the RAW request body for signature verification, so body parsing
//     is disabled via the exported `config` and we read the stream ourselves.
//   * The entitlement store path can be overridden with HMF_ENTITLEMENTS_PATH
//     (used by tests; in production the engine's default JSON store is used —
//     swap engine/entitlements.js's store for a real DB at scale).

'use strict';

const { grantEntitlement, revokeEntitlement } = require('../engine/entitlements');

// Stripe signature verification needs the exact raw bytes — do NOT let the
// platform parse the body first.
module.exports.config = {
  api: {
    bodyParser: false,
  },
};

// Collect the raw request body as a Buffer.
function readRawBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on('data', (chunk) => chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk)));
    req.on('end', () => resolve(Buffer.concat(chunks)));
    req.on('error', reject);
  });
}

// Optional store override (tests / configurable deployments). undefined => engine default.
function storePath() {
  const p = process.env.HMF_ENTITLEMENTS_PATH;
  return p && p.trim() !== '' ? p : undefined;
}

// Resolve a stable buyer identity from the completed session. This is the
// `subject` the delivery gate (api/download.js -> isEntitled) will key on.
// Prefer the metadata subject stamped at checkout, then the customer email,
// then the Stripe customer id, then client_reference_id.
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

// Resolve which pack(s) the buyer is entitled to. A specific pack id in metadata
// grants just that pack; a subscription with no specific pack grants the whole
// library ("*"). This mirrors engine/entitlements.js's packs contract.
function resolvePacks(session) {
  const meta = session.metadata || {};
  const pack = meta.pack || meta.packId || meta.pack_id;
  if (pack && String(pack).trim() !== '') return [String(pack)];
  // No specific pack => subscription-style access to everything.
  return '*';
}

module.exports = async function handler(req, res) {
  // ---- 1. Method guard ---------------------------------------------------
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'method_not_allowed', message: 'Use POST.' });
  }

  // ---- 2. Config guard: fail safe if unconfigured ------------------------
  const secretKey = process.env.STRIPE_SECRET_KEY;
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;
  if (!secretKey || !webhookSecret) {
    return res.status(501).json({
      error: 'not_configured',
      message:
        'Webhook is not configured. Founder must add STRIPE_SECRET_KEY and ' +
        'STRIPE_WEBHOOK_SECRET in Vercel env vars before purchases can grant access. See README.md.',
    });
  }

  // ---- 3. Verify the Stripe signature (fail-closed) ----------------------
  let event;
  try {
    // eslint-disable-next-line global-require
    const Stripe = require('stripe');
    const stripe = new Stripe(secretKey, { apiVersion: '2024-06-20' });

    const rawBody = await readRawBody(req);
    const signature = req.headers['stripe-signature'];

    // Throws on missing/invalid signature — that is the whole point.
    event = stripe.webhooks.constructEvent(rawBody, signature, webhookSecret);
  } catch (err) {
    console.error('[webhook] Signature verification failed:', err && err.message);
    return res
      .status(400)
      .json({ error: 'invalid_signature', message: 'Webhook signature verification failed.' });
  }

  // ---- 4. Handle the event -----------------------------------------------
  try {
    switch (event.type) {
      case 'checkout.session.completed': {
        const session = event.data.object || {};
        const subject = resolveSubject(session);
        const packs = resolvePacks(session);

        if (!subject) {
          // Paid but no usable identity — do not silently drop; 200 so Stripe
          // stops retrying, but log loudly for reconciliation.
          console.error('[webhook] checkout.session.completed with NO resolvable subject', {
            sessionId: session.id,
          });
          break;
        }

        // THE GRANT. After this, isEntitled(subject, packId) passes and
        // api/download.js will assemble + serve the ZIP for that buyer.
        const record = grantEntitlement(
          subject,
          {
            packs,
            source: 'stripe_webhook',
            session_id: session.id,
            email: (session.customer_details && session.customer_details.email) || null,
            customer: session.customer || null,
          },
          storePath()
        );

        // Also key the entitlement by the Stripe customer id when present and
        // distinct, so a later cancel/lapse can revoke by customer.
        if (session.customer && String(session.customer) !== subject) {
          grantEntitlement(String(session.customer), { packs, source: 'stripe_webhook', session_id: session.id }, storePath());
        }

        console.log('[webhook] ENTITLEMENT GRANT ->', JSON.stringify({
          subject,
          packs: record.packs,
          sessionId: session.id,
        }));
        break;
      }

      case 'customer.subscription.deleted': {
        // Subscription ended — revoke library access keyed by customer id.
        const sub = event.data.object || {};
        if (sub.customer) {
          revokeEntitlement(String(sub.customer), storePath());
          console.log('[webhook] revoked entitlement for customer', sub.customer);
        }
        break;
      }

      default:
        // Acknowledge unhandled events so Stripe stops retrying them.
        console.log('[webhook] unhandled event type:', event.type);
    }

    // Always 200 once we have safely processed (or intentionally ignored) it.
    return res.status(200).json({ received: true });
  } catch (err) {
    // If our own handling throws, return 500 so Stripe retries later.
    console.error('[webhook] handler error:', err && err.message);
    return res.status(500).json({ error: 'handler_error', message: 'Failed to process event.' });
  }
};
