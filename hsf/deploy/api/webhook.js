// api/webhook.js
//
// Hoch Storybook Factory (HSF) — Stripe webhook handler (STUB / scaffold).
//
// Responsibilities:
//   * Verify the Stripe signature using STRIPE_WEBHOOK_SECRET (never trust
//     an unsigned/forged event).
//   * On `checkout.session.completed`, log an entitlement grant. The actual
//     hosting/unlock work is marked with a clear TODO comment where the
//     founder (or a later build task) wires it up.
//
// SAFETY / DESIGN NOTES:
//   * FAILS SAFE: if STRIPE_SECRET_KEY or STRIPE_WEBHOOK_SECRET is missing,
//     we return 501 "not configured" instead of processing anything. The
//     scaffold is inert until the founder adds keys.
//   * We require the RAW request body to verify the signature. Vercel Node
//     functions expose it via a small helper below; we also disable body
//     parsing via the exported `config` so the raw bytes survive.
//
// Runtime: Node.js serverless function (CommonJS). Requires the `stripe`
// package at deploy time (see README).

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
        'STRIPE_WEBHOOK_SECRET in Vercel env vars. See hsf/deploy/README.md.',
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
        const tier = (session.metadata && session.metadata.tier) || 'unknown';
        const customerEmail =
          (session.customer_details && session.customer_details.email) || null;

        // Log the entitlement grant. In production this is where you would
        // record that this customer paid and is now entitled to export/host.
        console.log(
          '[webhook] ENTITLEMENT GRANT ->',
          JSON.stringify({
            tier,
            email: customerEmail,
            sessionId: session.id,
            mode: session.mode,
          })
        );

        // TODO (founder / later build task): actually grant the entitlement.
        //   - onestory: mark the specific story as "paid" and enable the
        //     high-res / watermark-free export + permanent hosting URL.
        //   - creators: create/activate the subscriber account so ALL their
        //     stories unlock while the subscription is active.
        // This is where hosting/unlock would happen (e.g. write to a DB,
        // flip a flag in KV/blob storage, or call a hosting API).
        break;
      }

      case 'customer.subscription.deleted': {
        // TODO (founder / later build task): revoke creator entitlements when
        // a subscription is canceled or lapses.
        console.log('[webhook] subscription ended:', event.data.object.id);
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
