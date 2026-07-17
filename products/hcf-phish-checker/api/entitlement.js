// api/entitlement.js
//
// HCF — Link & QR Safety Report — entitlement check (REAL).
//
// The delivery UI calls this to decide whether the report is unlocked:
//     GET /api/entitlement?session_id=<id>
// It reads the same record the signed webhook writes via lib/store.js:
//     sess:<id>   (one paid report)
//
// Fails OPEN-SAFE: unknown / missing keys return { paid:false } with HTTP 200.

'use strict';

const store = require('../lib/store');

module.exports = async function handler(req, res) {
  if (req.method && req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    return res.status(405).json({ error: 'method_not_allowed', message: 'Use GET.' });
  }

  const q = req.query || {};
  const sessionId = q.session_id ? String(q.session_id) : null;

  let paid = false;
  if (sessionId) {
    const rec = await store.get('sess:' + sessionId);
    if (rec && rec.paid === true) paid = true;
  }

  return res.status(200).json({ paid, source: paid ? 'session' : null });
};
