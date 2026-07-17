// api/export.js
//
// Hoch Storybook Factory (HSF) — paid export.  STUB (entitlement gate is REAL).
//
// The storefront POSTs { storyId, scenes, title } here and expects:
//   402  -> "Not paid yet — unlock first."   (story-studio-v2.html L409)
//   200 { url } -> the permanent share link
//
// WHAT IS REAL:  the entitlement gate. We read lib/store.js and return 402 if
//   the story (or the signed-in email) has not paid — this is the live half of
//   the buy loop and is covered by tests.
// WHAT IS A STUB:  the actual rendering + permanent hosting of the export. Once
//   entitlement is confirmed we currently return 501 not_implemented rather than
//   pretending a hosted URL exists. Wire real hosting here before go-live.

'use strict';

const store = require('../lib/store');

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

  const storyId = body.storyId ? String(body.storyId) : null;
  const email = body.email ? String(body.email).toLowerCase() : null;

  // ---- REAL entitlement gate -------------------------------------------
  const paid =
    (email && (await store.isPaid('email:' + email))) ||
    (storyId && (await store.isPaid('story:' + storyId)));

  if (!paid) {
    return res.status(402).json({
      error: 'payment_required',
      message: 'Not paid yet — unlock this story first.',
    });
  }

  // ---- STUB: hosting/render not implemented ----------------------------
  return res.status(501).json({
    error: 'not_implemented',
    stub: true,
    message:
      'STUB: entitlement verified, but permanent export/hosting is not ' +
      'implemented yet. Founder/next build wires real rendering + hosting here.',
  });
};
