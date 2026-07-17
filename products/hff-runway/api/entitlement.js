// api/entitlement.js
//
// HFF — Runway — entitlement check (REAL).
//
// The delivery UI calls this to decide whether to show the upload form or send
// the user to checkout:
//     GET /api/entitlement?email=<addr>
// It reads the same record the signed webhook writes via lib/store.js:
//     email:<addr>   (active $15/mo subscription)
//
// Fails OPEN-SAFE: unknown / missing keys return { paid:false } with HTTP 200,
// never an error, so the UI simply stays locked. No secrets required — works on
// the in-memory store locally and on Vercel KV in production.

'use strict';

const store = require('../lib/store');

module.exports = async function handler(req, res) {
  if (req.method && req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    return res.status(405).json({ error: 'method_not_allowed', message: 'Use GET.' });
  }

  const q = req.query || {};
  const email = q.email ? String(q.email).toLowerCase() : null;

  let paid = false;
  let tier = null;

  if (email) {
    const rec = await store.get('email:' + email);
    if (rec && rec.paid === true) {
      paid = true;
      tier = rec.tier || 'monthly';
    }
  }

  return res.status(200).json({ paid, tier, source: paid ? 'email' : null });
};
