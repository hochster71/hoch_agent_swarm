// api/generate-report.js
//
// HCF — Link & QR Safety Report generator endpoint. The paid/entitled user POSTs
// a URL (or a decoded QR payload) and gets back the offline heuristic report.
//
// ENTITLEMENT (one-time, session-keyed; mirrors the proven store gate). Access
// is granted if ANY of these holds:
//   1. STORE ENTITLEMENT — the signed webhook wrote `sess:<id>` paid:true when
//      the buyer checked out. Caller passes { session_id }; we read the store.
//   2. PAID SESSION — caller passes { session_id } and (when STRIPE_SECRET_KEY is
//      set) we verify the Checkout Session is paid directly with Stripe.
//   3. DEV UNLOCK — PHISH_DEV_UNLOCK=1 (local/dev only). NOT real payment.
//   Fails CLOSED otherwise (402 if we can point them to checkout, 501 if inert).
//
// GUARDRAIL: heuristic only. The engine's report-linter fails closed if a
// certainty over-claim ever appears, surfacing as 422 (never a fake success).

'use strict';

const { generateSafetyReport } = require('../engine');
const store = require('../lib/store');

async function isEntitled(req, body) {
  const devUnlock = process.env.PHISH_DEV_UNLOCK === '1';
  const secretKey = process.env.STRIPE_SECRET_KEY;
  const sessionId = body.session_id || (req.query && req.query.session_id);

  if (sessionId) {
    if (await store.isPaid('sess:' + sessionId)) return { ok: true, via: 'store' };
  }

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
    return { ok: false, code: 402, message: 'Payment required. Buy a report, then retry with your session_id.' };
  }
  return {
    ok: false,
    code: 501,
    message: 'Report generation is not configured. Set STRIPE_SECRET_KEY (buyers gate on session_id), or set PHISH_DEV_UNLOCK=1 for local testing. See README.md.',
  };
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
  if (!gate.ok) {
    return res.status(gate.code).json({ error: 'not_entitled', message: gate.message });
  }

  const input = body.input || body.url || body.payload;
  const kind = body.kind === 'qr' ? 'qr' : 'url';
  if (!input || typeof input !== 'string' || input.trim() === '') {
    return res.status(400).json({ error: 'no_input', message: 'Provide a link in the "input" field (or a decoded QR payload with kind:"qr").' });
  }

  try {
    const report = generateSafetyReport({ input, kind });
    return res.status(200).json({
      ok: true,
      dev_unlock: !!gate.dev,
      report: {
        kind: report.kind,
        input: report.input,
        normalizedUrl: report.normalizedUrl,
        payload: report.payload,
        band: report.band,
        score: report.score,
        meaning: report.meaning,
        redirectChainStatic: report.redirectChainStatic,
        findings: report.findings,
        disclaimer: report.disclaimer,
        text: report.text,
        generatedAt: report.generatedAt,
      },
    });
  } catch (err) {
    const code = err.code === 'REPORT_LINTER_FAILED' ? 422
      : (err.code === 'UNPARSEABLE_URL' || err.code === 'EMPTY_INPUT') ? 400 : 400;
    return res.status(code).json({ error: err.code || 'engine_error', message: err.message });
  }
};
