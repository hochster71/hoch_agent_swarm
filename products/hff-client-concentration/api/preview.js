// api/preview.js
//
// FREE preview — deliberately NOT entitlement-gated. Runs the real engine on the
// uploaded CSV and returns the top-line concentration figures plus the first
// three client labels, so a stranger can see the tool actually works before
// paying.
//
// What it withholds (the paid part): the full per-client table, per-client
// payment timing and dormancy detail, the monthly series, per-invoice rows,
// flagged-row detail, and the XLSX + PDF artifacts. Nothing here is fabricated —
// it is a genuine subset of the same deterministic run.
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
      concentration: {
        top1SharePct: s.concentration.top1SharePct,
        top3SharePct: s.concentration.top3SharePct,
        effectiveClientCount: s.concentration.effectiveClientCount,
        hhi: s.concentration.hhi,
      },
      window: s.window,
      dateOrder: report.dateOrder,
      topClients: report.analysis.clients
        .filter((c) => c.net > 0)
        .slice(0, 3)
        .map((c) => ({ label: c.label, sharePct: c.sharePct, invoiceCount: c.invoiceCount })),
      withheld:
        'Full per-client table, per-client payment timing and dormancy detail, the monthly revenue series, ' +
        'per-invoice rows, flagged-row detail, the XLSX workbook and the PDF summary are unlocked after purchase.',
      disclaimer: report.disclaimer,
    });
  } catch (err) {
    const code = ['EMPTY_FILE', 'NO_ROWS', 'MISSING_COLUMNS', 'NO_VALID_ROWS', 'BAD_INPUT_TYPE'].includes(err.code) ? 400
      : ['FILE_TOO_LARGE', 'TOO_MANY_ROWS'].includes(err.code) ? 413
      : err.code === 'ADVICE_LINTER_FAILED' ? 422 : 400;
    return res.status(code).json({ error: err.code || 'engine_error', message: err.message });
  }
};
