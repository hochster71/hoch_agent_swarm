// api/preview.js
//
// FREE preview — deliberately NOT entitlement-gated. Runs the real engine on the
// uploaded CSV and returns the top-line spend figures plus the first three
// vendor labels, so a stranger can see the tool actually works before paying.
//
// What it withholds (the paid part): the full per-vendor table, per-vendor
// cadence / dormancy / drift detail, the monthly series, the category rollup,
// per-payment rows, flagged-row detail, and the XLSX + PDF artifacts. Nothing
// here is fabricated — it is a genuine subset of the same deterministic run.
'use strict';

const { analyze } = require('../engine');

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

  const csv = body.csv || body.file || body.text;
  if (!csv || typeof csv !== 'string') {
    return res.status(400).json({ error: 'no_csv', message: 'Provide the CSV contents in the "csv" field.' });
  }

  try {
    const report = analyze(csv, { dateOrder: body.dateOrder });
    const s = report.summary;
    return res.status(200).json({
      ok: true,
      preview: true,
      counts: s.counts,
      spend: s.spend,
      concentration: {
        top1SharePct: s.concentration.top1SharePct,
        top3SharePct: s.concentration.top3SharePct,
        vendorsForHalfOfSpend: s.concentration.vendorsForHalfOfSpend,
      },
      window: s.window,
      dateOrder: report.dateOrder,
      topVendors: report.analysis.vendors
        .slice(0, 3)
        .map((v) => ({
          label: v.label,
          net: v.net,
          netSharePct: v.netSharePct,
          paymentCount: v.paymentCount,
        })),
      withheld:
        'The full per-vendor table (cadence, dormancy, amount drift, min/median/max payment, merged spellings), ' +
        'the monthly series, the category rollup, per-payment rows, flagged-row detail, the XLSX workbook and ' +
        'the PDF summary are unlocked after purchase.',
      disclaimer: report.disclaimer,
    });
  } catch (err) {
    const code = ['EMPTY_FILE', 'NO_ROWS', 'MISSING_COLUMNS', 'NO_VALID_ROWS', 'BAD_INPUT_TYPE'].includes(err.code) ? 400
      : ['FILE_TOO_LARGE', 'TOO_MANY_ROWS'].includes(err.code) ? 413
      : err.code === 'ADVICE_LINTER_FAILED' ? 422 : 400;
    return res.status(code).json({ error: err.code || 'engine_error', message: err.message });
  }
};
