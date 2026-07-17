// test/buyloop.test.js
//
// HFF Invoice Aging — buy-loop verification with node:test.
//
// SCOPE / HONESTY: this is a LOGIC-LEVEL, TEST-MODE verification. Stripe is MOCKED (no
// `stripe` package call, no network, no keys) and the entitlement store runs on its
// in-memory fallback (no Vercel KV). It proves the code paths of checkout -> signed
// webhook -> entitlement -> gated report generation are coherent. It is NOT a live run
// and NOT a real Stripe test-mode run (which would need founder keys + network).
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

const SAMPLE_CSV = [
  'Invoice,Customer,Due Date,Amount,Amount Paid',
  'INV-1,Acme Corp,2026-03-31,4200.00,0',
  'INV-2,Brightline LLC,2026-05-02,1800.00,300.00',
  'INV-3,Cedar & Co,2026-06-15,600.00,0',
].join('\n');

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
    data: { object: { id: 'cs_test_123', mode: 'payment', metadata: { product: 'hff-invoice-aging', tier: 'report' }, customer_details: { email: 'buyer@example.com' } } },
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
  await store.setPaid('sess:cs_abc', { tier: 'report' });
  const handler = load('api/entitlement.js');
  const res = makeRes();
  await handler({ method: 'GET', query: { session_id: 'cs_abc' } }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.paid, true);
  assert.strictEqual(res.body.tier, 'report');
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
// (c) generate-report gate: allows entitled buyer, denies un-entitled
// ===========================================================================
test('generate-report DENIES an un-entitled request (402 when Stripe configured)', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  delete process.env.AGING_DEV_UNLOCK;
  await store._reset();
  sessionPaid = false; // even if a session_id were checked, it's unpaid
  const handler = load('api/generate-report.js');
  const res = makeRes();
  await handler({ method: 'POST', body: { session_id: 'cs_unpaid', csv: SAMPLE_CSV }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 402);
  assert.strictEqual(res.body.error, 'not_entitled');
  sessionPaid = true;
});

test('generate-report DENIES with 501 when totally unconfigured (no key, no dev unlock)', async () => {
  delete process.env.STRIPE_SECRET_KEY;
  delete process.env.AGING_DEV_UNLOCK;
  await store._reset();
  const handler = load('api/generate-report.js');
  const res = makeRes();
  await handler({ method: 'POST', body: { csv: SAMPLE_CSV }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 501);
  assert.strictEqual(res.body.error, 'not_entitled');
});

test('generate-report ALLOWS a buyer with a webhook-written session entitlement (re-download)', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  delete process.env.AGING_DEV_UNLOCK;
  await store._reset();
  await store.setPaid('sess:cs_paid', { tier: 'report' });
  const handler = load('api/generate-report.js');

  let res = makeRes();
  await handler({ method: 'POST', body: { session_id: 'cs_paid', csv: SAMPLE_CSV }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.ok, true);
  assert.ok(res.body.files.xlsxBase64 && res.body.files.pdfBase64, 'expected report file bytes');

  // Re-download of the same purchase works too.
  res = makeRes();
  await handler({ method: 'POST', body: { session_id: 'cs_paid', csv: SAMPLE_CSV }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.ok, true);
});

test('generate-report ALLOWS on a fresh paid session_id (first run right after checkout)', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  delete process.env.AGING_DEV_UNLOCK;
  await store._reset();
  sessionPaid = true;
  const handler = load('api/generate-report.js');
  const res = makeRes();
  await handler({ method: 'POST', body: { session_id: 'cs_fresh', csv: SAMPLE_CSV }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.ok, true);
});

// ===========================================================================
// (d) END-TO-END: checkout(mocked) -> signed webhook grant -> gated generate ok
// ===========================================================================
test('END-TO-END: checkout -> webhook grant -> entitled generate (all mocked/in-memory)', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  process.env.STRIPE_WEBHOOK_SECRET = 'whsec_MOCK_NOT_REAL';
  process.env.STRIPE_PRICE_REPORT = 'price_MOCK';
  delete process.env.AGING_DEV_UNLOCK;
  await store._reset();
  const SID = 'cs_e2e';

  // 1. Checkout session created (mocked stripe returns a url).
  let res = makeRes();
  await (load('api/create-checkout-session.js'))(
    { method: 'POST', body: { tier: 'report' }, headers: { origin: 'https://example.test' } }, res
  );
  assert.strictEqual(res.statusCode, 200);
  assert.ok(res.body.url);

  // 2. Before the webhook lands, a store lookup for this session is unpaid.
  assert.strictEqual(await store.isPaid('sess:' + SID), false);

  // 3. Stripe fires a SIGNED checkout.session.completed -> webhook writes grant.
  currentEvent = {
    type: 'checkout.session.completed',
    data: { object: { id: SID, mode: 'payment', metadata: { product: 'hff-invoice-aging', tier: 'report' }, customer_details: { email: 'e2e@example.com' } } },
  };
  res = makeRes();
  await (load('api/webhook.js'))(rawReq('{}', { 'stripe-signature': 'good' }), res);
  assert.strictEqual(res.statusCode, 200);

  // 4. Now the same session can generate a report.
  res = makeRes();
  await (load('api/generate-report.js'))({ method: 'POST', body: { session_id: SID, csv: SAMPLE_CSV }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.ok, true);
  assert.ok(res.body.summary.totalOutstanding > 0);
});
