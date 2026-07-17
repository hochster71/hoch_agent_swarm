// test/buyloop.test.js
//
// HCF — Link & QR Safety Report — buy-loop verification with node:test.
//
// SCOPE / HONESTY: LOGIC-LEVEL, TEST-MODE verification. Stripe is MOCKED (no
// `stripe` package call, no network, no keys) and the entitlement store runs on
// its in-memory fallback (no Vercel KV). It proves the code paths of checkout ->
// signed webhook -> entitlement -> gated report generation are coherent. It is
// NOT a live run and NOT a real Stripe test-mode run.
//
// Run:  node test/buyloop.test.js

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
    const e = new Error("Cannot find module '@vercel/kv'");
    e.code = 'MODULE_NOT_FOUND';
    throw e;
  }
  return origLoad.apply(this, arguments);
};

const store = require(path.join(ROOT, 'lib', 'store.js'));

const SAMPLE_URL = 'https://paypal.account-verify.com/login';

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
  req.method = 'POST';
  req.headers = headers || {};
  return req;
}

// ---- webhook ----
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

test('webhook writes a one-time entitlement on checkout.session.completed', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  process.env.STRIPE_WEBHOOK_SECRET = 'whsec_MOCK_NOT_REAL';
  await store._reset();
  currentEvent = {
    type: 'checkout.session.completed',
    data: { object: { id: 'cs_test_123', mode: 'payment', metadata: { product: 'hcf-phish-checker', tier: 'report' }, customer_details: { email: 'b@example.com' } } },
  };
  const handler = load('api/webhook.js');
  const res = makeRes();
  await handler(rawReq(JSON.stringify({ ok: 1 }), { 'stripe-signature': 'good' }), res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(await store.isPaid('sess:cs_test_123'), true);
});

// ---- entitlement route ----
test('entitlement route returns { paid:true } for a granted session', async () => {
  await store._reset();
  await store.setPaid('sess:cs_abc', { tier: 'report' });
  const handler = load('api/entitlement.js');
  const res = makeRes();
  await handler({ method: 'GET', query: { session_id: 'cs_abc' } }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.paid, true);
});
test('entitlement route returns { paid:false } for an unknown session', async () => {
  await store._reset();
  const handler = load('api/entitlement.js');
  const res = makeRes();
  await handler({ method: 'GET', query: { session_id: 'cs_unknown' } }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.paid, false);
});

// ---- generate-report gate ----
test('generate-report DENIES an un-entitled request (402 when Stripe configured)', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  delete process.env.PHISH_DEV_UNLOCK;
  await store._reset();
  sessionPaid = false;
  const handler = load('api/generate-report.js');
  const res = makeRes();
  await handler({ method: 'POST', body: { session_id: 'cs_unpaid', input: SAMPLE_URL }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 402);
  assert.strictEqual(res.body.error, 'not_entitled');
  sessionPaid = true;
});

test('generate-report DENIES with 501 when totally unconfigured', async () => {
  delete process.env.STRIPE_SECRET_KEY;
  delete process.env.PHISH_DEV_UNLOCK;
  await store._reset();
  const handler = load('api/generate-report.js');
  const res = makeRes();
  await handler({ method: 'POST', body: { session_id: 'cs_x', input: SAMPLE_URL }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 501);
  assert.strictEqual(res.body.error, 'not_entitled');
});

test('generate-report ALLOWS an entitled session and returns a heuristic report', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  delete process.env.PHISH_DEV_UNLOCK;
  await store._reset();
  await store.setPaid('sess:cs_paid', { tier: 'report' });
  const handler = load('api/generate-report.js');
  const res = makeRes();
  await handler({ method: 'POST', body: { session_id: 'cs_paid', input: SAMPLE_URL }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.ok, true);
  assert.strictEqual(res.body.report.band, 'HIGH');
  assert.ok(res.body.report.disclaimer && res.body.report.disclaimer.length > 20);
});

test('generate-report ALLOWS on a fresh paid session_id (verified with Stripe)', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  delete process.env.PHISH_DEV_UNLOCK;
  await store._reset();
  sessionPaid = true;
  const handler = load('api/generate-report.js');
  const res = makeRes();
  await handler({ method: 'POST', body: { session_id: 'cs_fresh', input: 'https://example.com' }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.ok, true);
});

// ---- END-TO-END ----
test('END-TO-END: checkout -> webhook grant -> entitled report (all mocked/in-memory)', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  process.env.STRIPE_WEBHOOK_SECRET = 'whsec_MOCK_NOT_REAL';
  process.env.STRIPE_PRICE_REPORT = 'price_MOCK';
  delete process.env.PHISH_DEV_UNLOCK;
  await store._reset();
  sessionPaid = false; // force reliance on the webhook-written grant, not a live retrieve

  // 1. Checkout session created (mocked).
  let res = makeRes();
  await (load('api/create-checkout-session.js'))({ method: 'POST', body: { tier: 'report' }, headers: { origin: 'https://example.test' } }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.ok(res.body.url);

  // 2. Before payment, generate is denied.
  res = makeRes();
  await (load('api/generate-report.js'))({ method: 'POST', body: { session_id: 'cs_e2e', input: SAMPLE_URL }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 402);

  // 3. Stripe fires a SIGNED checkout.session.completed -> webhook writes grant.
  currentEvent = { type: 'checkout.session.completed', data: { object: { id: 'cs_e2e', mode: 'payment', metadata: { tier: 'report' }, customer_details: { email: 'e2e@example.com' } } } };
  res = makeRes();
  await (load('api/webhook.js'))(rawReq('{}', { 'stripe-signature': 'good' }), res);
  assert.strictEqual(res.statusCode, 200);

  // 4. Now that session can generate a report.
  res = makeRes();
  await (load('api/generate-report.js'))({ method: 'POST', body: { session_id: 'cs_e2e', input: SAMPLE_URL }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.ok, true);
  sessionPaid = true;
});
