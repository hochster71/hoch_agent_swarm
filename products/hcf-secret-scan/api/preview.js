// api/preview.js
//
// HCF — Secret & Key Exposure Scan — FREE, UNGATED preview.
//
// Anyone can paste text and see: HOW MANY credential-shaped patterns matched at
// each severity, how many were set aside as likely placeholders, and the
// concern band. It does NOT reveal which patterns matched, where, or their
// masked values — that is the paid scan.
//
// No entitlement is required and no payment path is touched. The engine's
// fail-closed linter still runs, so the guardrail applies to free output too.
'use strict';

const { previewText } = require('../engine');

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

  const text = body.text || body.input || body.content;
  if (!text || typeof text !== 'string' || text.trim() === '') {
    return res.status(400).json({ error: 'no_input', message: 'Provide the text to scan in the "text" field.' });
  }

  try {
    return res.status(200).json({ ok: true, preview: previewText(text) });
  } catch (err) {
    const code = err.code === 'REPORT_LINTER_FAILED' ? 422 : 400;
    return res.status(code).json({ error: err.code || 'engine_error', message: err.message });
  }
};
