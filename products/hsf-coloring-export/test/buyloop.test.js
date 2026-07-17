// test/buyloop.test.js
//
// HSF — Coloring Book Export — buy-loop verification with node:test.
//
// SCOPE / HONESTY: this is a LOGIC-LEVEL, TEST-MODE verification. Stripe is MOCKED (no
// `stripe` package call, no network, no keys) and the entitlement store runs on its
// in-memory fallback (no Vercel KV). It proves the code paths of checkout -> signed
// webhook -> entitlement -> watermark-free gated export are coherent. It is NOT a live
// run and NOT a real Stripe test-mode run (which would need founder keys + network).
//
// Run:  node test/buyloop.test.js       (node:test auto-runs)

'use strict';

const test = require('node:test');
const assert = require('node:assert');
const Module = require('node:module');
const path = require('node:path');
const { Readable } = require('node:stream');

const ROOT = path.resolve(__dirname, '..');

let currentEvent = null;
let sessionPaid = true;

function makeFakeStripe() {
  return function Stripe(_key, _cfg) {
    return {
      checkout: {
        sessions: {
          create: async () => ({ id: 'cs_mock', url: 'https://checkout.stripe.com/pay/cs_mock' }),
          retrieve: async (id) => ({ id, payment_status: sessionPaid ? 'paid' : 'unpaid', status: sessionPaid ? 'complete' : 'open' }),
        },
      },
      webhooks: {
        constructEvent: (_raw, sig, _secret) => {
          if (sig !== 'good') throw new Error('No signatures found matching the expected signature.');
          return currentEvent;
        },
      },
    };
  };
}

const origLoad = Module._load;
Module._load = function (request) {
  if (request === 'stripe') return makeFakeStripe();
  if (request === '@vercel/kv') {
    const e = new Error("Cannot find module '@vercel/kv'"); e.code = 'MODULE_NOT_FOUND'; throw e;
  }
  return origLoad.apply(this, arguments);
};

const store = require(path.join(ROOT, 'lib', 'store.js'));

const SAFE_STORY = {
  title: 'Maya the Brave Gardener',
  scenes: [
    { kicker: 'Prologue', heading: 'Maya the Brave Gardener', body: 'A girl who planted a garden on the moon.' },
    { kicker: 'The Journey', heading: 'Up the silver ladder', body: 'Seeds in her pocket, stars in her hair.' },
    { kicker: 'The Next Launch', heading: 'The moon bloomed', body: 'And everyone came to picnic in the flowers.' },
  ],
};

const WATERMARK = 'PREVIEW - PURCHASE TO REMOVE WATERMARK';
function hasWatermark(b64) { return Buffer.from(b64, 'base64').toString('latin1').includes(WATERMARK); }

function makeRes() {
  const res = { statusCode: 200, body: null, headers: {} };
  res.status = (c) => { res.statusCode = c; return res; };
  res.json = (o) => { res.body = o; return res; };
  res.setHeader = (k, v) => { res.headers[k] = v; };
  return res;
}
function load(rel) {
  const p = require.resolve(path.join(ROOT, rel));
  delete require.cache[p];
  return require(p);
}
function rawReq(bodyStr, headers) {
  const req = Readable.from([Buffer.from(bodyStr)]);
  req.method = 'POST'; req.headers = headers || {};
  return req;
}

// ===========================================================================
// (a) webhook: config guard, bad signature, valid grant
// ===========================================================================
test('webhook returns 501 when unconfigured (no keys)', async () => {
  delete process.env.STRIPE_SECRET_KEY;
  delete process.env.STRIPE_WEBHOOK_SECRET;
  const handler = load('api/webhook.js');
  const res = makeRes();
  await handler(rawReq('{}', { 'stripe-signature': 'good' }), res);
  assert.strictEqual(res.statusCode, 501);
  assert.strictEqual(res.body.error, 'not_configured');
});

test('webhook rejects a bad signature with 400 (fails closed)', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  process.env.STRIPE_WEBHOOK_SECRET = 'whsec_MOCK_NOT_REAL';
  currentEvent = null;
  const handler = load('api/webhook.js');
  const res = makeRes();
  await handler(rawReq('{}', { 'stripe-signature': 'bad' }), res);
  assert.strictEqual(res.statusCode, 400);
  assert.strictEqual(res.body.error, 'invalid_signature');
});

test('webhook writes session entitlement on valid checkout.session.completed', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  process.env.STRIPE_WEBHOOK_SECRET = 'whsec_MOCK_NOT_REAL';
  await store._reset();
  currentEvent = {
    type: 'checkout.session.completed',
    data: { object: { id: 'cs_test_123', mode: 'payment', metadata: { product: 'hsf-coloring-export', tier: 'export' }, customer_details: { email: 'buyer@example.com' } } },
  };
  const handler = load('api/webhook.js');
  const res = makeRes();
  await handler(rawReq(JSON.stringify({ ok: 1 }), { 'stripe-signature': 'good' }), res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.received, true);
  assert.strictEqual(await store.isPaid('sess:cs_test_123'), true);
});

// ===========================================================================
// (b) entitlement route reflects the webhook-written grant
// ===========================================================================
test('entitlement route returns { paid:true } for a granted session', async () => {
  await store._reset();
  await store.setPaid('sess:cs_abc', { tier: 'export' });
  const handler = load('api/entitlement.js');
  const res = makeRes();
  await handler({ method: 'GET', query: { session_id: 'cs_abc' } }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.paid, true);
  assert.strictEqual(res.body.tier, 'export');
});

test('entitlement route returns { paid:false } for an unknown session', async () => {
  await store._reset();
  const handler = load('api/entitlement.js');
  const res = makeRes();
  await handler({ method: 'GET', query: { session_id: 'cs_nope' } }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.paid, false);
});

// ===========================================================================
// (c) export gate: free preview is ALWAYS watermarked; watermark-free is gated
// ===========================================================================
test('free preview works with NO keys at all — but is ALWAYS watermarked', async () => {
  delete process.env.STRIPE_SECRET_KEY;
  delete process.env.COLORING_DEV_UNLOCK;
  await store._reset();
  const handler = load('api/export-coloring-book.js');
  const res = makeRes();
  await handler({ method: 'POST', body: { story: SAFE_STORY }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.ok, true);
  assert.strictEqual(res.body.watermarked, true);
  assert.ok(hasWatermark(res.body.files.pdfBase64), 'preview PDF must carry the watermark');
});

test('watermark-free DENIED with 501 when totally unconfigured (no key, no dev unlock)', async () => {
  delete process.env.STRIPE_SECRET_KEY;
  delete process.env.COLORING_DEV_UNLOCK;
  await store._reset();
  const handler = load('api/export-coloring-book.js');
  const res = makeRes();
  await handler({ method: 'POST', body: { story: SAFE_STORY, watermark_free: true }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 501);
  assert.strictEqual(res.body.error, 'not_entitled');
});

test('watermark-free DENIED with 402 for an un-entitled request (Stripe configured)', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  delete process.env.COLORING_DEV_UNLOCK;
  await store._reset();
  sessionPaid = false;
  const handler = load('api/export-coloring-book.js');
  const res = makeRes();
  await handler({ method: 'POST', body: { story: SAFE_STORY, watermark_free: true, session_id: 'cs_unpaid' }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 402);
  assert.strictEqual(res.body.error, 'not_entitled');
  sessionPaid = true;
});

test('watermark-free ALLOWED for a webhook-written entitlement; PDF has NO watermark; re-export works', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  delete process.env.COLORING_DEV_UNLOCK;
  await store._reset();
  await store.setPaid('sess:cs_paid', { tier: 'export' });
  const handler = load('api/export-coloring-book.js');

  let res = makeRes();
  await handler({ method: 'POST', body: { story: SAFE_STORY, watermark_free: true, session_id: 'cs_paid' }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.watermarked, false);
  assert.ok(!hasWatermark(res.body.files.pdfBase64), 'paid export must be watermark-free');

  // Re-export of the same purchase works too.
  res = makeRes();
  await handler({ method: 'POST', body: { story: SAFE_STORY, watermark_free: true, session_id: 'cs_paid' }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.watermarked, false);
});

test('safety gate applies even to a PAID export (child-safe is not for sale)', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  await store._reset();
  await store.setPaid('sess:cs_paid2', { tier: 'export' });
  const handler = load('api/export-coloring-book.js');
  const res = makeRes();
  await handler({
    method: 'POST',
    body: {
      story: { scenes: [{ kicker: 'Scene', heading: 'Bad page', body: 'The hero grabbed his shotgun.' }] },
      watermark_free: true,
      session_id: 'cs_paid2',
    },
    headers: {},
  }, res);
  assert.strictEqual(res.statusCode, 422);
  assert.strictEqual(res.body.error, 'SAFETY_GATE_FAILED');
});

// ===========================================================================
// (d) END-TO-END: checkout(mocked) -> signed webhook grant -> watermark-free export
// ===========================================================================
test('END-TO-END: checkout -> webhook grant -> watermark-free export (all mocked/in-memory)', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  process.env.STRIPE_WEBHOOK_SECRET = 'whsec_MOCK_NOT_REAL';
  process.env.STRIPE_PRICE_EXPORT = 'price_MOCK';
  delete process.env.COLORING_DEV_UNLOCK;
  await store._reset();
  const SID = 'cs_e2e';

  // 1. Checkout session created (mocked stripe returns a url).
  let res = makeRes();
  await (load('api/create-checkout-session.js'))(
    { method: 'POST', body: { tier: 'export' }, headers: { origin: 'https://example.test' } }, res
  );
  assert.strictEqual(res.statusCode, 200);
  assert.ok(res.body.url);

  // 2. Before the webhook lands, a store lookup for this session is unpaid.
  assert.strictEqual(await store.isPaid('sess:' + SID), false);

  // 3. Stripe fires a SIGNED checkout.session.completed -> webhook writes grant.
  currentEvent = {
    type: 'checkout.session.completed',
    data: { object: { id: SID, mode: 'payment', metadata: { product: 'hsf-coloring-export', tier: 'export' }, customer_details: { email: 'e2e@example.com' } } },
  };
  res = makeRes();
  await (load('api/webhook.js'))(rawReq('{}', { 'stripe-signature': 'good' }), res);
  assert.strictEqual(res.statusCode, 200);

  // 4. Now the same session exports watermark-free.
  res = makeRes();
  await (load('api/export-coloring-book.js'))({ method: 'POST', body: { story: SAFE_STORY, watermark_free: true, session_id: SID }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.ok, true);
  assert.strictEqual(res.body.watermarked, false);
  assert.ok(!hasWatermark(res.body.files.pdfBase64));
  assert.strictEqual(res.body.pages, SAFE_STORY.scenes.length + 2);
});
