// api/webhook.js
//
// HRF — Clarity Briefs — Stripe webhook handler (REAL, zero-dependency).
//
// Responsibilities:
//   * Verify the Stripe signature using STRIPE_WEBHOOK_SECRET on every event.
//     Fail-closed: a missing/forged signature returns 400 and NOTHING is written.
//   * On `checkout.session.completed`, grant an entitlement token that the
//     existing Python gate (`engine/entitlement.py`) accepts, via lib/entitlements.
//   * On subscription cancel/lapse, revoke best-effort.
//
// SIGNATURE VERIFICATION — WHY NO `stripe` PACKAGE:
//   Stripe's webhook signature is a documented HMAC-SHA256 scheme. We implement
//   exactly that scheme with Node's built-in `crypto` (constant-time compare +
//   timestamp tolerance), so this route has ZERO third-party dependencies and is
//   fully testable offline — consistent with the engine's zero-dep design.
//   Header format:  `t=<unix_ts>,v1=<hex_hmac>`  over payload  `<t>.<rawBody>`.
//   This is equivalent to `stripe.webhooks.constructEvent(...)`.
//
// SAFETY:
//   * FAILS SAFE: if STRIPE_WEBHOOK_SECRET is missing, returns 501 "not
//     configured" and processes nothing. Inert until the founder sets the secret.
//   * Requires the RAW request body — body parsing is disabled via `config`.
//
// Runtime: Node.js serverless function (CommonJS).

'use strict';

const crypto = require('crypto');
const { grant, revoke } = require('../lib/entitlements');

// Tell Vercel NOT to parse the body — signature verification needs raw bytes.
module.exports.config = { api: { bodyParser: false } };

const DEFAULT_TOLERANCE_SEC = 300; // reject events older than 5 min (replay guard)

function readRawBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on('data', (chunk) => chunks.push(Buffer.from(chunk)));
    req.on('end', () => resolve(Buffer.concat(chunks)));
    req.on('error', reject);
  });
}

// Verify Stripe's `Stripe-Signature` header and return the parsed event.
// Throws on any failure — the caller turns that into a 400.
function constructEvent(rawBody, header, secret, toleranceSec = DEFAULT_TOLERANCE_SEC) {
  if (!header || typeof header !== 'string') throw new Error('missing Stripe-Signature header');

  const fields = {};
  for (const part of header.split(',')) {
    const idx = part.indexOf('=');
    if (idx === -1) continue;
    const k = part.slice(0, idx).trim();
    const v = part.slice(idx + 1).trim();
    if (k === 'v1') (fields.v1 = fields.v1 || []).push(v);
    else fields[k] = v;
  }
  const t = fields.t;
  const v1list = fields.v1;
  if (!t || !v1list || v1list.length === 0) throw new Error('malformed signature header');

  const payloadStr = typeof rawBody === 'string' ? rawBody : rawBody.toString('utf8');
  const expected = crypto
    .createHmac('sha256', secret)
    .update(`${t}.${payloadStr}`, 'utf8')
    .digest('hex');
  const expBuf = Buffer.from(expected, 'utf8');

  // Accept if ANY provided v1 signature matches (Stripe may send several).
  const matched = v1list.some((sig) => {
    const sigBuf = Buffer.from(sig, 'utf8');
    return sigBuf.length === expBuf.length && crypto.timingSafeEqual(sigBuf, expBuf);
  });
  if (!matched) throw new Error('signature mismatch — no v1 matched');

  if (toleranceSec > 0) {
    const now = Math.floor(Date.now() / 1000);
    const ts = Number(t);
    if (!Number.isFinite(ts) || Math.abs(now - ts) > toleranceSec) {
      throw new Error('timestamp outside tolerance');
    }
  }

  return JSON.parse(payloadStr);
}

module.exports = async function handler(req, res) {
  // ---- 1. Method guard ---------------------------------------------------
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'method_not_allowed', message: 'Use POST.' });
  }

  // ---- 2. Config guard: fail safe if unconfigured -----------------------
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;
  if (!webhookSecret || webhookSecret.trim() === '') {
    return res.status(501).json({
      error: 'not_configured',
      message:
        'Webhook is not configured. Founder must add STRIPE_WEBHOOK_SECRET in ' +
        'Vercel env vars. See README.md.',
    });
  }

  // ---- 3. Verify the signature (fail-closed) ----------------------------
  let event;
  try {
    const rawBody = await readRawBody(req);
    const signature = req.headers['stripe-signature'];
    event = constructEvent(rawBody, signature, webhookSecret);
  } catch (err) {
    console.error('[webhook] signature verification failed:', err && err.message);
    return res
      .status(400)
      .json({ error: 'invalid_signature', message: 'Webhook signature verification failed.' });
  }

  // ---- 4. Handle the event ----------------------------------------------
  try {
    switch (event.type) {
      case 'checkout.session.completed': {
        const session = event.data.object || {};
        const tier = (session.metadata && session.metadata.tier) || 'brief';
        const email = (session.customer_details && session.customer_details.email) || null;

        // The Stripe checkout session id IS the entitlement token. It is unique,
        // stable, and shown to the buyer on the success page so they can redeem
        // it on the generate form. The Python gate accepts it verbatim.
        const token = session.id;
        if (!token) {
          console.warn('[webhook] checkout.session.completed without a session id; skipped.');
          break;
        }
        const rec = grant(token, tier, {
          email,
          sessionId: session.id,
          mode: session.mode || null,
        });
        console.log(
          '[webhook] ENTITLEMENT GRANTED ->',
          JSON.stringify({ token, tier, remaining: rec.remaining, email })
        );
        break;
      }

      case 'customer.subscription.deleted': {
        // Best-effort revoke: if the subscription carries the originating
        // checkout token in metadata, zero its credits. Full customer->token
        // mapping for lifecycle revocation is a documented follow-up.
        const sub = event.data.object || {};
        const token = (sub.metadata && sub.metadata.token) || null;
        if (token) {
          revoke(token);
          console.log('[webhook] entitlement revoked ->', token);
        } else {
          console.log('[webhook] subscription.deleted with no mapped token; logged only.');
        }
        break;
      }

      default:
        // Acknowledge so Stripe stops retrying.
        console.log('[webhook] unhandled event type:', event.type);
    }

    return res.status(200).json({ received: true });
  } catch (err) {
    // Our own handling failed -> 500 so Stripe retries later.
    console.error('[webhook] handler error:', err && err.message);
    return res.status(500).json({ error: 'handler_error', message: 'Failed to process event.' });
  }
};

// Exported for tests (offline signature construction/verification).
module.exports.constructEvent = constructEvent;
