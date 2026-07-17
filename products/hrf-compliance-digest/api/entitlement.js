// api/entitlement.js
//
// HRF — Compliance Change Digest — entitlement check (REAL).
//   GET /api/entitlement?email=<addr>  -> { paid, tier }
// Reads the same record the signed webhook writes (email:<addr>). Fails OPEN-SAFE.

'use strict';

const store = require('../lib/store');

module.exports = async function handler(req, res) {
  if (req.method && req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    return res.status(405).json({ error: 'method_not_allowed', message: 'Use GET.' });
  }
  const q = req.query || {};
  const email = q.email ? String(q.email).toLowerCase() : null;
  let paid = false, tier = null;
  if (email) {
    const rec = await store.get('email:' + email);
    if (rec && rec.paid === true) { paid = true; tier = rec.tier || 'monthly'; }
  }
  return res.status(200).json({ paid, tier, source: paid ? 'email' : null });
};
