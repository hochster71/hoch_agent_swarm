// api/export-coloring-book.js
//
// HSF — Coloring Book Export — the delivery endpoint.
//
// POST { story, session_id?, watermark_free? } ->
//   * WATERMARKED PREVIEW: always available, free — that's the funnel. The
//     child-safety gate still applies (fail-closed).
//   * WATERMARK-FREE EXPORT (watermark_free: true): PAID outcome. Granted only if:
//       1. STORE ENTITLEMENT — the signed webhook wrote `sess:<id>` paid:true.
//          Caller passes { session_id }; durable, allows re-export.
//       2. PAID SESSION — (when STRIPE_SECRET_KEY is set) the Checkout Session is
//          verified paid directly with Stripe (first export right after checkout,
//          before the webhook lands).
//       3. DEV UNLOCK — COLORING_DEV_UNLOCK=1 (local/dev only). NOT real payment.
//     Fails CLOSED otherwise (402 if we can point to checkout, 501 if inert).
//
// GUARDRAILS: child-facing -> engine safety gate is mandatory and runs on BOTH
// paths; the watermark is stripped ONLY here, only after the entitlement gate.
// No secrets hardcoded. No money moved here.

'use strict';

const { generateColoringBook } = require('../engine');
const store = require('../lib/store');

async function isEntitled(req, body) {
  const devUnlock = process.env.COLORING_DEV_UNLOCK === '1';
  const secretKey = process.env.STRIPE_SECRET_KEY;
  const sessionId = body.session_id || (req.query && req.query.session_id);

  // 1. Durable store entitlement (webhook-written) — allows re-export.
  if (sessionId) {
    if (await store.isPaid('sess:' + sessionId)) return { ok: true, via: 'store' };
  }

  // 2. Fresh paid Checkout Session (first export right after checkout).
  if (secretKey && secretKey.trim() !== '' && sessionId) {
    try {
      const Stripe = require('stripe');
      const stripe = new Stripe(secretKey, { apiVersion: '2024-06-20' });
      const session = await stripe.checkout.sessions.retrieve(sessionId);
      const paid = session && (session.payment_status === 'paid' || session.status === 'complete');
      if (paid) return { ok: true, via: 'session' };
      return { ok: false, code: 402, message: 'Checkout session is not paid.' };
    } catch (e) {
      return { ok: false, code: 402, message: 'Could not verify checkout session.' };
    }
  }

  // 3. Dev unlock (no payments wired).
  if (devUnlock) return { ok: true, dev: true };

  if (secretKey && secretKey.trim() !== '') {
    return { ok: false, code: 402, message: 'Payment required for a watermark-free export. Purchase, then retry with your session_id.' };
  }
  return {
    ok: false,
    code: 501,
    message:
      'Watermark-free export is not configured. Set STRIPE_SECRET_KEY (buyers gate on ' +
      'their checkout session_id), or set COLORING_DEV_UNLOCK=1 for local testing. ' +
      'The watermarked preview remains free. See README.md.',
  };
}

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

  if (!body.story || typeof body.story !== 'object') {
    return res.status(400).json({ error: 'no_story', message: 'Provide a "story" object ({ scenes: [...] } or { spec: {...} }).' });
  }

  // Decide the mode FIRST; strip the watermark only behind the gate.
  let watermarkFree = false;
  let gateInfo = null;
  if (body.watermark_free === true) {
    const gate = await isEntitled(req, body);
    if (!gate.ok) {
      return res.status(gate.code).json({ error: 'not_entitled', message: gate.message });
    }
    watermarkFree = true;
    gateInfo = gate;
  }

  try {
    const result = generateColoringBook({ story: body.story, watermarkFree });
    return res.status(200).json({
      ok: true,
      dev_unlock: !!(gateInfo && gateInfo.dev),
      title: result.title,
      pages: result.pages,
      scenes: result.scenes,
      droppedScenes: result.droppedScenes,
      watermarked: result.watermarked,
      files: {
        pdfName: result.files.pdfName,
        pdfBase64: result.files.pdf.toString('base64'),
      },
    });
  } catch (err) {
    const code = err.code === 'SAFETY_GATE_FAILED' ? 422 : err.code === 'BAD_INPUT' ? 400 : 400;
    return res.status(code).json({ error: err.code || 'engine_error', message: err.message, category: err.category || undefined });
  }
};
