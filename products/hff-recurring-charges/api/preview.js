// api/preview.js
//
// FREE preview — deliberately NOT entitlement-gated. Runs the real engine on the
// uploaded CSV and returns the top-line counts plus the first three merchant
// labels so a stranger can see the tool actually works before paying.
//
// What it withholds (the paid part): the full per-merchant table, cadence and
// confidence detail, per-occurrence rows, flagged-row detail, and the XLSX + PDF
// artifacts. Nothing here is fabricated — it is a genuine subset of the same
// deterministic run.
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
      totals: s.totals,
      window: s.window,
      dateOrder: report.dateOrder,
      sampleMerchants: report.detection.recurring.slice(0, 3).map((r) => ({
        label: r.label, cadence: r.cadence, occurrences: r.occurrences,
      })),
      withheld: 'Full per-merchant table, cadence/confidence detail, per-occurrence rows, flagged-row detail, XLSX workbook and PDF summary are unlocked after purchase.',
      disclaimer: report.disclaimer,
    });
  } catch (err) {
    const code = ['EMPTY_FILE', 'NO_ROWS', 'MISSING_COLUMNS', 'NO_VALID_ROWS', 'BAD_INPUT_TYPE'].includes(err.code) ? 400
      : ['FILE_TOO_LARGE', 'TOO_MANY_ROWS'].includes(err.code) ? 413
      : err.code === 'ADVICE_LINTER_FAILED' ? 422 : 400;
    return res.status(code).json({ error: err.code || 'engine_error', message: err.message });
  }
};
