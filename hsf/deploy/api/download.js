// api/download.js
//
// Hoch Storybook Factory (HSF) — download a paid export. STUB (gate is REAL).
//
// Referenced by vercel.json (/api/download). Not yet called by the current UI.
// Same contract shape as export: entitlement is enforced for real; the actual
// file delivery is a STUB (501 not_implemented) until hosting is wired.

'use strict';

const store = require('../lib/store');

module.exports = async function handler(req, res) {
  const q = req.query || {};
  const body = (typeof req.body === 'object' && req.body) || {};
  const storyId = q.storyId ? String(q.storyId) : (body.storyId ? String(body.storyId) : null);
  const email = q.email ? String(q.email).toLowerCase() : (body.email ? String(body.email).toLowerCase() : null);

  // ---- REAL entitlement gate -------------------------------------------
  const paid =
    (email && (await store.isPaid('email:' + email))) ||
    (storyId && (await store.isPaid('story:' + storyId)));

  if (!paid) {
    return res.status(402).json({
      error: 'payment_required',
      message: 'Not paid yet — unlock this story before downloading.',
    });
  }

  // ---- STUB: file delivery not implemented -----------------------------
  return res.status(501).json({
    error: 'not_implemented',
    stub: true,
    message: 'STUB: entitlement verified, but download delivery is not implemented yet.',
  });
};
