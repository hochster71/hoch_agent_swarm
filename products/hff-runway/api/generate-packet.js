// api/generate-packet.js
//
// HFF — Runway packet generator endpoint. The paid/entitled user POSTs their transactions
// CSV here and gets back the XLSX + PDF packet.
//
// ENTITLEMENT (mirrors the checkout's fail-safe shape):
//   * Access is gated on a PAID Stripe Checkout Session. Caller passes { session_id }.
//     If STRIPE_SECRET_KEY is set, we verify session.payment_status === 'paid' before running.
//   * If STRIPE_SECRET_KEY is NOT set, the route is INERT (501) UNLESS RUNWAY_DEV_UNLOCK=1 is
//     set (local/dev only) — this lets the founder test the engine without wiring payments.
//     This is NOT real payment; the real gate is the Stripe session check.
//   * No secrets are hardcoded. No money is moved here.
//
// GUARDRAIL: organizational tooling only; the engine itself refuses to emit advice language.

'use strict';

const { generateRunwayPacket } = require('../engine');

async function isEntitled(req, body) {
  const devUnlock = process.env.RUNWAY_DEV_UNLOCK === '1';
  const secretKey = process.env.STRIPE_SECRET_KEY;

  // Real gate: verify a paid Stripe checkout session.
  if (secretKey && secretKey.trim() !== '') {
    const sessionId = body.session_id || (req.query && req.query.session_id);
    if (!sessionId) return { ok: false, code: 401, message: 'Missing session_id (paid checkout required).' };
    try {
      const Stripe = require('stripe');
      const stripe = new Stripe(secretKey, { apiVersion: '2024-06-20' });
      const session = await stripe.checkout.sessions.retrieve(sessionId);
      const paid = session && (session.payment_status === 'paid' || session.status === 'complete');
      if (!paid) return { ok: false, code: 402, message: 'Checkout session is not paid.' };
      return { ok: true };
    } catch (e) {
      return { ok: false, code: 402, message: 'Could not verify checkout session.' };
    }
  }

  // No payment configured: allow only if the founder explicitly opted into dev-unlock.
  if (devUnlock) return { ok: true, dev: true };

  return {
    ok: false,
    code: 501,
    message:
      'Packet generation is not configured. Set STRIPE_SECRET_KEY (and gate on a paid session), ' +
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
