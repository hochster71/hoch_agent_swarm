// api/generate-digest.js
//
// HRF — Compliance Change Digest generator endpoint. The paid/entitled subscriber
// POSTs their source docs + drafted change-claims and gets back a linted, cited
// digest (JSON + rendered markdown), or a fail-closed 422 if a claim is uncited
// or a quote isn't grounded.
//
// ENTITLEMENT (subscription-aware; mirrors hff-runway):
//   1. STORE ENTITLEMENT — signed webhook wrote email:<addr> paid:true.
//   2. PAID SESSION — { session_id } verified with Stripe (first run after checkout).
//   3. DEV UNLOCK — DIGEST_DEV_UNLOCK=1 (local only). NOT real payment.
//   Fails CLOSED otherwise (402 with Stripe configured, 501 when inert).
//
// GUARDRAIL: information not legal advice; citation-per-claim enforced by the
// engine's fail-closed linter (surfaces as 422 — never a fake success).

'use strict';

const { buildDigest } = require('../engine');
const store = require('../lib/store');

async function isEntitled(req, body) {
  const devUnlock = process.env.DIGEST_DEV_UNLOCK === '1';
  const secretKey = process.env.STRIPE_SECRET_KEY;
  const email = (body.email || (req.query && req.query.email) || '').toString().trim().toLowerCase();
  const sessionId = body.session_id || (req.query && req.query.session_id);

  if (email && (await store.isPaid('email:' + email))) return { ok: true, via: 'subscription' };

  if (secretKey && secretKey.trim() !== '' && sessionId) {
    try {
      const Stripe = require('stripe');
      const stripe = new Stripe(secretKey, { apiVersion: '2024-06-20' });
      const session = await stripe.checkout.sessions.retrieve(sessionId);
      const paid = session && (session.payment_status === 'paid' || session.status === 'complete');
      if (paid) return { ok: true, via: 'session' };
      return { ok: false, code: 402, message: 'Checkout session is not paid.' };
    } catch (e) {
      return { ok: false, code: 402, message: 'Could not verify checkout session.' };
    }
  }

  if (devUnlock) return { ok: true, dev: true };

  if (secretKey && secretKey.trim() !== '') {
    return { ok: false, code: 402, message: 'Subscription required. Subscribe, then retry with your email.' };
  }
  return { ok: false, code: 501, message: 'Digest generation is not configured. Set STRIPE_SECRET_KEY (subscribers gate on email), or DIGEST_DEV_UNLOCK=1 for local testing. See README.md.' };
}

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'method_not_allowed', message: 'Use POST.' });
  }

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body || '{}'); }
    catch (e) { return res.status(400).json({ error: 'bad_json', message: 'Body is not valid JSON.' }); }
  }
  body = body || {};

  const gate = await isEntitled(req, body);
  if (!gate.ok) return res.status(gate.code).json({ error: 'not_entitled', message: gate.message });

  const request = body.request && typeof body.request === 'object' ? body.request : body;
  if (!Array.isArray(request.sources) || !Array.isArray(request.changes)) {
    return res.status(400).json({ error: 'bad_request', message: 'Provide { sources:[...], changes:[...] } (each change needs >=1 citation into a source).' });
  }

  try {
    const { digest, markdown } = buildDigest(request);
    return res.status(200).json({
      ok: true,
      dev_unlock: !!gate.dev,
      coverage_pct: digest.coverage_pct,
      digest,
      markdown,
    });
  } catch (err) {
    const code = err.code === 'DIGEST_LINT_FAILED' ? 422 : 400;
    return res.status(code).json({
      error: err.code || 'engine_error',
      message: err.message,
      violations: err.result ? err.result.violations : undefined,
    });
  }
};
