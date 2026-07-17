// api/entitlement.js
//
// Hoch Storybook Factory (HSF) — entitlement check (REAL).
//
// The storefront calls this on load:
//     GET /api/entitlement?storyId=<id>              (story-studio-v2.html L655)
// and unlocks the export UI when the response is { paid: true }.
//
// It reads the same records the signed webhook writes via lib/store.js:
//     story:<storyId>   (onestory one-time export)
//     email:<addr>      (creators subscription — passed as ?email=)
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
  const storyId = q.storyId ? String(q.storyId) : null;
  const email = q.email ? String(q.email).toLowerCase() : null;

  let paid = false;
  let tier = null;
  let source = null;

  // Creators subscription (by email) unlocks everything.
  if (email) {
    const rec = await store.get('email:' + email);
    if (rec && rec.paid === true) {
      paid = true;
      tier = rec.tier || 'creators';
      source = 'email';
    }
  }

  // Otherwise check this specific story's one-time entitlement.
  if (!paid && storyId) {
    const rec = await store.get('story:' + storyId);
    if (rec && rec.paid === true) {
      paid = true;
      tier = rec.tier || 'onestory';
      source = 'story';
    }
  }

  return res.status(200).json({ paid, tier, source });
};
