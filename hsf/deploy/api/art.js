// api/art.js
//
// Hoch Storybook Factory (HSF) — scene illustration. STUB.
//
// Storefront POSTs { art_prompt, storyId } and handles:
//   402 -> "Upgrade required to paint illustrations." (story-studio-v2.html L432)
//   501 -> "OpenAI keys are not configured. Paint is inert." (L436)
//
// STUB: no image model is wired. We enforce the entitlement gate (402 if unpaid)
// and otherwise return 501 not_implemented — honest, no fake images.

'use strict';

const store = require('../lib/store');

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'method_not_allowed', message: 'Use POST.' });
  }
  const body = (typeof req.body === 'object' && req.body) || {};
  const storyId = body.storyId ? String(body.storyId) : null;
  const email = body.email ? String(body.email).toLowerCase() : null;

  const paid =
    (email && (await store.isPaid('email:' + email))) ||
    (storyId && (await store.isPaid('story:' + storyId)));

  if (!paid) {
    return res.status(402).json({ error: 'payment_required', message: 'Upgrade required to paint illustrations.' });
  }

  // STUB: no image generation model is configured in this scaffold.
  return res.status(501).json({
    error: 'not_implemented',
    stub: true,
    message: 'STUB: illustration generation is not wired. No image model configured.',
  });
};
