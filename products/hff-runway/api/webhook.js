// api/webhook.js
//
// HFF — Runway — Stripe webhook handler (REAL entitlement grant).
//
// Responsibilities:
//   * Verify the Stripe signature using STRIPE_WEBHOOK_SECRET (never trust an
//     unsigned/forged event). FAILS CLOSED (400) on a bad/missing signature.
//   * On `checkout.session.completed`, write the buyer's entitlement to the
//     store (lib/store.js), keyed by their email. That unlocks repeat packet
//     generation for an active subscriber.
//   * On `customer.subscription.deleted` / `.updated`, revoke or re-grant so a
//     lapsed subscriber loses access (via the cust:<id> -> email map).
//
// SAFETY / DESIGN NOTES (mirrors the proven hsf/deploy/api/webhook.js):
//   * FAILS SAFE: if STRIPE_SECRET_KEY or STRIPE_WEBHOOK_SECRET is missing, we
//     return 501 "not configured" and process nothing — inert until keys added.
//   * We require the RAW request body to verify the signature, so body parsing
//     is disabled via the exported `config`.
//   * No secrets are hardcoded. No money is moved here.
//
// Runtime: Node.js serverless function (CommonJS). Requires the `stripe` package
// at deploy time.

'use strict';

// Tell Vercel NOT to parse the body — Stripe signature verification needs the
// exact raw bytes. We read the stream manually in `readRawBody` below.
module.exports.config = {
  api: {
    bodyParser: false,
  },
};

// Collect the raw request body as a Buffer.
function readRawBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on('data', (chunk) => chunks.push(chunk));
    req.on('end', () => resolve(Buffer.concat(chunks)));
    req.on('error', reject);
  });
}

module.exports = async function handler(req, res) {
  // ---- 1. Method guard ---------------------------------------------------
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res
      .status(405)
      .json({ error: 'method_not_allowed', message: 'Use POST.' });
  }

  // ---- 2. Config guard: fail safe if unconfigured -----------------------
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

  // ---- 3. Verify the Stripe signature -----------------------------------
  let event;
  try {
    // eslint-disable-next-line global-require
    const Stripe = require('stripe');
    const stripe = new Stripe(secretKey, { apiVersion: '2024-06-20' });

    const rawBody = await readRawBody(req);
    const signature = req.headers['stripe-signature'];

    // Throws if the signature is missing/invalid — that's the whole point.
    event = stripe.webhooks.constructEvent(rawBody, signature, webhookSecret);
  } catch (err) {
    console.error('[webhook] Signature verification failed:', err && err.message);
    return res
      .status(400)
      .json({ error: 'invalid_signature', message: 'Webhook signature verification failed.' });
  }

  // ---- 4. Handle the event ----------------------------------------------
  try {
    switch (event.type) {
      case 'checkout.session.completed': {
        const session = event.data.object;
        const customerEmail =
          (session.customer_details && session.customer_details.email) ||
          session.customer_email ||
          null;

        console.log(
          '[webhook] ENTITLEMENT GRANT ->',
          JSON.stringify({
            email: customerEmail,
            sessionId: session.id,
            mode: session.mode,
          })
        );

        // Grant the subscription entitlement, keyed by email (repeat generation).
        const { setPaid, put } = require('../lib/store');
        if (customerEmail) {
          await setPaid('email:' + customerEmail.toLowerCase(), {
            tier: 'monthly',
            product: 'hff-runway',
            sessionId: session.id,
          });
          // Map Stripe customer -> email so we can revoke on cancel/lapse.
          if (session.customer) {
            await put('cust:' + session.customer, { email: customerEmail });
          }
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
          if (sub.status === 'active' || sub.status === 'trialing')
            await setPaid('email:' + m.email.toLowerCase(), { tier: 'monthly', product: 'hff-runway', via: 'sub.updated' });
          else await setUnpaid('email:' + m.email.toLowerCase());
        }
        break;
      }

      default:
        // Acknowledge unhandled events so Stripe stops retrying them.
        console.log('[webhook] unhandled event type:', event.type);
    }

    // Always 200 once we've safely processed (or intentionally ignored) it.
    return res.status(200).json({ received: true });
  } catch (err) {
    // If our own handling throws, return 500 so Stripe retries later.
    console.error('[webhook] handler error:', err && err.message);
    return res
      .status(500)
      .json({ error: 'handler_error', message: 'Failed to process event.' });
  }
};
