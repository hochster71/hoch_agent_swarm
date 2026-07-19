// api/preview.js
//
// HCF — Email Header Audit — FREE, UNGATED preview.
//
// Anyone can paste headers and see: the sender identity as stated, the hop
// count, whether authentication results are present at all, and HOW MANY signals
// matched at each severity. It does NOT reveal which signals matched or what
// they mean — that is the paid audit.
//
// No entitlement is required and no payment path is touched. The engine's
// fail-closed linter still runs, so the guardrail applies to free output too.
'use strict';

const { previewHeaders } = require('../engine');

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

  const headersText = body.headers || body.input || body.text;
  if (!headersText || typeof headersText !== 'string' || headersText.trim() === '') {
    return res.status(400).json({ error: 'no_input', message: 'Provide the raw header block in the "headers" field.' });
  }

  try {
    return res.status(200).json({ ok: true, preview: previewHeaders(headersText) });
  } catch (err) {
    const code = err.code === 'REPORT_LINTER_FAILED' ? 422 : 400;
    return res.status(code).json({ error: err.code || 'engine_error', message: err.message });
  }
};
