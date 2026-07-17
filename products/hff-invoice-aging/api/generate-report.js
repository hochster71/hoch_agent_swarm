// api/generate-report.js
//
// HFF — Invoice Aging report generator endpoint. The paid/entitled user POSTs their
// AR/invoice CSV here and gets back the XLSX + one-page PDF aging report.
//
// ENTITLEMENT (one-time purchase; mirrors the proven hff entitlement store):
//   Invoice Aging is a $9 ONE-TIME purchase, gated by the checkout SESSION. Access is
//   granted if ANY of these holds:
//     1. STORE ENTITLEMENT — the signed webhook wrote `sess:<id>` paid:true when the
//        buyer checked out. Caller passes { session_id }; we read the store. This is the
//        durable gate that also lets the buyer re-download their report.
//     2. PAID SESSION — caller passes { session_id } and (when STRIPE_SECRET_KEY is set)
//        we verify the Checkout Session is paid directly with Stripe. Covers the very
//        first generation right after checkout, before the webhook has landed.
//     3. DEV UNLOCK — AGING_DEV_UNLOCK=1 (local/dev only). NOT real payment.
//   Fails CLOSED otherwise (402 if we can point them to checkout, 501 if inert).
//   No secrets hardcoded. No money moved here.
//
// GUARDRAIL: organizational tooling only; the engine itself refuses to emit advice language.

'use strict';

const { generateAgingReport } = require('../engine');
const store = require('../lib/store');

async function isEntitled(req, body) {
  const devUnlock = process.env.AGING_DEV_UNLOCK === '1';
  const secretKey = process.env.STRIPE_SECRET_KEY;
  const sessionId = body.session_id || (req.query && req.query.session_id);

  // 1. Durable store entitlement (webhook-written) — allows re-download.
  if (sessionId) {
    if (await store.isPaid('sess:' + sessionId)) return { ok: true, via: 'store' };
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

  if (secretKey && secretKey.trim() !== '') {
    return { ok: false, code: 402, message: 'Payment required. Purchase, then retry with your session_id.' };
  }
  return {
    ok: false,
    code: 501,
    message:
      'Report generation is not configured. Set STRIPE_SECRET_KEY (buyers gate on their ' +
      'checkout session_id), or set AGING_DEV_UNLOCK=1 for local testing. See README.md.',
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

  const csv = body.csv;
  if (!csv || typeof csv !== 'string' || csv.trim() === '') {
    return res.status(400).json({ error: 'no_csv', message: 'Provide an AR/invoice CSV in the "csv" field.' });
  }
  const profile = body.profile && typeof body.profile === 'object' ? body.profile : {};

  try {
    const result = await generateAgingReport({ csv, profile });
    return res.status(200).json({
      ok: true,
      dev_unlock: !!gate.dev,
      validation: result.validation,
      summary: {
        asOf: result.report.aging.asOf,
        outstandingInvoices: result.report.aging.outstandingCount,
        paidExcluded: result.report.aging.paidCount,
        flaggedRows: result.report.rejected.length,
        totalOutstanding: result.report.aging.totalOutstanding,
        buckets: result.report.aging.buckets.map((b) => ({ label: b.label, balance: b.balance, count: b.count })),
        topCustomer: result.report.byCustomer[0] ? result.report.byCustomer[0].customer : null,
      },
      files: {
        xlsxName: result.files.xlsxName,
        pdfName: result.files.pdfName,
        xlsxBase64: result.files.xlsx.toString('base64'),
        pdfBase64: result.files.pdf.toString('base64'),
      },
    });
  } catch (err) {
    const code = err.code === 'ADVICE_LINTER_FAILED' || err.code === 'VALIDATION_FAILED' ? 422 : 400;
    return res.status(code).json({ error: err.code || 'engine_error', message: err.message });
  }
};
