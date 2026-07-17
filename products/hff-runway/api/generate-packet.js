// api/generate-packet.js
//
// HFF — Runway packet generator endpoint. The paid/entitled user POSTs their transactions
// CSV here and gets back the XLSX + PDF packet.
//
// ENTITLEMENT (subscription-aware; mirrors the proven hsf entitlement store):
//   Runway is a $15/mo subscription, so an active subscriber must be able to
//   generate packets REPEATEDLY. Access is granted if ANY of these holds:
//     1. STORE ENTITLEMENT — the signed webhook wrote `email:<addr>` paid:true
//        when the buyer checked out. Caller passes { email }; we read the store.
//        This is the durable, repeat-use gate for subscribers.
//     2. PAID SESSION — caller passes { session_id } and (when STRIPE_SECRET_KEY
//        is set) we verify the Checkout Session is paid. This covers the very
//        first generation right after checkout, before/without the email lookup.
//     3. DEV UNLOCK — RUNWAY_DEV_UNLOCK=1 (local/dev only) lets the founder test
//        the engine with no payments wired. NOT real payment.
//   Fails CLOSED otherwise (402 if we can point them to checkout, 501 if inert).
//   * No secrets are hardcoded. No money is moved here.
//
// GUARDRAIL: organizational tooling only; the engine itself refuses to emit advice language.

'use strict';

const { generateRunwayPacket } = require('../engine');
const store = require('../lib/store');

async function isEntitled(req, body) {
  const devUnlock = process.env.RUNWAY_DEV_UNLOCK === '1';
  const secretKey = process.env.STRIPE_SECRET_KEY;
  const email = (body.email || (req.query && req.query.email) || '').toString().trim().toLowerCase();
  const sessionId = body.session_id || (req.query && req.query.session_id);

  // 1. Durable store entitlement (active subscriber) — allows repeat generation.
  if (email) {
    if (await store.isPaid('email:' + email)) return { ok: true, via: 'subscription' };
  }

  // 2. Fresh paid Checkout Session (first run right after checkout).
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

  // 3. Dev unlock (no payments wired).
  if (devUnlock) return { ok: true, dev: true };

  // Not entitled. If Stripe is configured, this is a payment-required case;
  // otherwise the route is inert until the founder wires keys.
  if (secretKey && secretKey.trim() !== '') {
    return { ok: false, code: 402, message: 'Subscription required. Subscribe, then retry with your email.' };
  }
  return {
    ok: false,
    code: 501,
    message:
      'Packet generation is not configured. Set STRIPE_SECRET_KEY (subscribers gate on their email), ' +
      'or set RUNWAY_DEV_UNLOCK=1 for local testing. See README.md.',
  };
}

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'method_not_allowed', message: 'Use POST.' });
  }

  let body = req.body;
  if (typeof body === 'string') {
    try {
      body = JSON.parse(body || '{}');
    } catch (e) {
      return res.status(400).json({ error: 'bad_json', message: 'Body is not valid JSON.' });
    }
  }
  body = body || {};

  const gate = await isEntitled(req, body);
  if (!gate.ok) {
    return res.status(gate.code).json({ error: 'not_entitled', message: gate.message });
  }

  const csv = body.csv;
  if (!csv || typeof csv !== 'string' || csv.trim() === '') {
    return res.status(400).json({ error: 'no_csv', message: 'Provide a transactions CSV in the "csv" field.' });
  }
  const profile = body.profile && typeof body.profile === 'object' ? body.profile : {};

  try {
    const result = await generateRunwayPacket({ csv, profile });
    return res.status(200).json({
      ok: true,
      dev_unlock: !!gate.dev,
      validation: result.validation,
      summary: {
        asOf: result.packet.cashflow.asOf,
        transactions: result.packet.transactions.length,
        flaggedRows: result.packet.rejected.length,
        estimatedQuarterlyPayment: result.packet.estTax.quarterlyPayment,
        candidates1099: result.packet.list1099.filter((c) => c.isCandidate).length,
      },
      files: {
        xlsxName: result.files.xlsxName,
        pdfName: result.files.pdfName,
        xlsxBase64: result.files.xlsx.toString('base64'),
        pdfBase64: result.files.pdf.toString('base64'),
      },
    });
  } catch (err) {
    // Fail-closed errors (advice linter / validation) surface as 422, not a fake success.
    const code = err.code === 'ADVICE_LINTER_FAILED' || err.code === 'VALIDATION_FAILED' ? 422 : 400;
    return res.status(code).json({ error: err.code || 'engine_error', message: err.message });
  }
};
