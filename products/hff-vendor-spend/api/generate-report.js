// api/generate-report.js
//
// HFF — Vendor Spend Rollup — PAID report endpoint. Returns the full report
// JSON plus the XLSX workbook and one-page PDF as base64.
//
// ENTITLEMENT (one-time, session-keyed; identical gate to the proven products):
//   1. STORE ENTITLEMENT — the signed webhook wrote `sess:<id>` paid:true.
//   2. PAID SESSION — with STRIPE_SECRET_KEY set, verify the Checkout Session
//      directly with Stripe.
//   3. DEV UNLOCK — VENDORSPEND_DEV_UNLOCK=1 (local/dev only). NOT real payment.
//   Fails CLOSED otherwise (402 when we can point at checkout, 501 when inert).
//
// GUARDRAIL: the engine's advice linter fails closed before any artifact bytes
// are produced. A violation surfaces as 422 — never a fake success, and never a
// partially-rendered artifact.
'use strict';

const { buildReport } = require('../engine');
const store = require('../lib/store');

async function isEntitled(req, body) {
  const devUnlock = process.env.VENDORSPEND_DEV_UNLOCK === '1';
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
    message: 'Report generation is not configured. Set STRIPE_SECRET_KEY (buyers gate on session_id), or set VENDORSPEND_DEV_UNLOCK=1 for local testing. See README.md.',
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
  if (!gate.ok) return res.status(gate.code).json({ error: 'not_entitled', message: gate.message });

  const csv = body.csv || body.file || body.text;
  if (!csv || typeof csv !== 'string') {
    return res.status(400).json({ error: 'no_csv', message: 'Provide the CSV contents in the "csv" field.' });
  }

  try {
    const { report, xlsx, pdf } = buildReport(csv, { dateOrder: body.dateOrder });
    return res.status(200).json({
      ok: true,
      dev_unlock: !!gate.dev,
      entitled_via: gate.via || (gate.dev ? 'dev' : null),
      report: {
        summary: report.summary,
        vendors: report.analysis.vendors.map((v) => {
          const { rows, ...rest } = v;
          return rest;
        }),
        monthly: report.analysis.monthly,
        categories: report.analysis.categories,
        concentration: report.analysis.concentration,
        totals: report.analysis.totals,
        skipped: report.skipped,
        dateOrder: report.dateOrder,
        amountMode: report.amountMode,
        disclaimer: report.disclaimer,
      },
      files: {
        xlsx: { filename: 'vendor-spend-rollup.xlsx', base64: xlsx.toString('base64'), bytes: xlsx.length },
        pdf: { filename: 'vendor-spend-summary.pdf', base64: pdf.toString('base64'), bytes: pdf.length },
      },
    });
  } catch (err) {
    const code = ['EMPTY_FILE', 'NO_ROWS', 'MISSING_COLUMNS', 'NO_VALID_ROWS', 'BAD_INPUT_TYPE'].includes(err.code) ? 400
      : ['FILE_TOO_LARGE', 'TOO_MANY_ROWS'].includes(err.code) ? 413
      : err.code === 'ADVICE_LINTER_FAILED' ? 422 : 400;
    return res.status(code).json({ error: err.code || 'engine_error', message: err.message });
  }
};
