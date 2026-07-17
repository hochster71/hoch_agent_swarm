// api/entitlement.js
//
// HFF — Invoice Aging — entitlement check (REAL).
//
// The delivery UI calls this to decide whether to show the upload form or send the
// user to checkout:
//     GET /api/entitlement?session_id=<id>
// It reads the same record the signed webhook writes via lib/store.js:
//     sess:<sessionId>   (one-time $9 purchase)
//
// Fails OPEN-SAFE: unknown / missing keys return { paid:false } with HTTP 200, never
// an error, so the UI simply stays locked. No secrets required.

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
  let tier = null;

  if (sessionId) {
    const rec = await store.get('sess:' + sessionId);
    if (rec && rec.paid === true) { paid = true; tier = rec.tier || 'report'; }
  }

  return res.status(200).json({ paid, tier, source: paid ? 'session' : null });
};
