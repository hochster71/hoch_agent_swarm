// test/buyloop.test.js
//
// HRF — Compliance Change Digest — buy-loop verification with node:test.
//
// SCOPE / HONESTY: LOGIC-LEVEL, TEST-MODE. Stripe is MOCKED and the entitlement
// store uses its in-memory fallback. Proves checkout -> signed webhook ->
// entitlement -> gated digest generation is coherent. NOT a live Stripe run.
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
  return function Stripe() {
    return {
      checkout: { sessions: {
        create: async () => ({ id: 'cs_mock', url: 'https://checkout.stripe.com/pay/cs_mock' }),
        retrieve: async (id) => ({ id, payment_status: sessionPaid ? 'paid' : 'unpaid', status: sessionPaid ? 'complete' : 'open' }),
      } },
      webhooks: { constructEvent: (_raw, sig) => { if (sig !== 'good') throw new Error('bad sig'); return currentEvent; } },
    };
  };
}

const origLoad = Module._load;
Module._load = function (request) {
  if (request === 'stripe') return makeFakeStripe();
  if (request === '@vercel/kv') { const e = new Error("Cannot find module '@vercel/kv'"); e.code = 'MODULE_NOT_FOUND'; throw e; }
  return origLoad.apply(this, arguments);
};

const store = require(path.join(ROOT, 'lib', 'store.js'));

const REQUEST = {
  topic: 'Data Protection Rule Update 2027',
  sources: [{ id: 's1', title: 'Notice', url: 'https://example.gov/n', text: 'covered entities must complete an annual assessment.' }],
  changes: [{ text: 'Annual assessment now required.', affects: ['covered entities'],
    citations: [{ source_id: 's1', quote: 'covered entities must complete an annual assessment' }] }],
};

function makeRes() {
  const res = { statusCode: 200, body: null, headers: {} };
  res.status = (c) => { res.statusCode = c; return res; };
  res.json = (o) => { res.body = o; return res; };
  res.setHeader = (k, v) => { res.headers[k] = v; };
  return res;
}
function load(rel) { const p = require.resolve(path.join(ROOT, rel)); delete require.cache[p]; return require(p); }
function rawReq(bodyStr, headers) { const req = Readable.from([Buffer.from(bodyStr)]); req.method = 'POST'; req.headers = headers || {}; return req; }

test('webhook returns 501 when unconfigured', async () => {
  delete process.env.STRIPE_SECRET_KEY; delete process.env.STRIPE_WEBHOOK_SECRET;
  const res = makeRes();
  await load('api/webhook.js')(rawReq('{}', { 'stripe-signature': 'good' }), res);
  assert.strictEqual(res.statusCode, 501);
});

test('webhook rejects a bad signature with 400 (fails closed)', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK'; process.env.STRIPE_WEBHOOK_SECRET = 'whsec_MOCK';
  currentEvent = null;
  const res = makeRes();
  await load('api/webhook.js')(rawReq('{}', { 'stripe-signature': 'bad' }), res);
  assert.strictEqual(res.statusCode, 400);
  assert.strictEqual(res.body.error, 'invalid_signature');
});

test('webhook grants subscription on checkout.session.completed', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK'; process.env.STRIPE_WEBHOOK_SECRET = 'whsec_MOCK';
  await store._reset();
  currentEvent = { type: 'checkout.session.completed', data: { object: { id: 'cs_1', mode: 'subscription', customer_details: { email: 'Buyer@Example.com' }, customer: 'cus_1' } } };
  const res = makeRes();
  await load('api/webhook.js')(rawReq('{}', { 'stripe-signature': 'good' }), res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(await store.isPaid('email:buyer@example.com'), true);
  const map = await store.get('cust:cus_1');
  assert.strictEqual(map && map.email, 'Buyer@Example.com');
});

test('webhook revokes on customer.subscription.deleted', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK'; process.env.STRIPE_WEBHOOK_SECRET = 'whsec_MOCK';
  await store._reset();
  await store.setPaid('email:buyer@example.com', { tier: 'monthly' });
  await store.put('cust:cus_1', { email: 'buyer@example.com' });
  currentEvent = { type: 'customer.subscription.deleted', data: { object: { customer: 'cus_1' } } };
  const res = makeRes();
  await load('api/webhook.js')(rawReq('{}', { 'stripe-signature': 'good' }), res);
  assert.strictEqual(await store.isPaid('email:buyer@example.com'), false);
});

test('entitlement route reflects webhook grant', async () => {
  await store._reset();
  await store.setPaid('email:buyer@example.com', { tier: 'monthly' });
  const res = makeRes();
  await load('api/entitlement.js')({ method: 'GET', query: { email: 'Buyer@Example.com' } }, res);
  assert.strictEqual(res.body.paid, true);
  assert.strictEqual(res.body.tier, 'monthly');
});

test('generate-digest DENIES un-entitled (402 when Stripe configured)', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK'; delete process.env.DIGEST_DEV_UNLOCK;
  await store._reset();
  const res = makeRes();
  await load('api/generate-digest.js')({ method: 'POST', body: Object.assign({ email: 'nobody@example.com' }, REQUEST), headers: {} }, res);
  assert.strictEqual(res.statusCode, 402);
});

test('generate-digest DENIES 501 when totally unconfigured', async () => {
  delete process.env.STRIPE_SECRET_KEY; delete process.env.DIGEST_DEV_UNLOCK;
  await store._reset();
  const res = makeRes();
  await load('api/generate-digest.js')({ method: 'POST', body: Object.assign({ email: 'nobody@example.com' }, REQUEST), headers: {} }, res);
  assert.strictEqual(res.statusCode, 501);
});

test('generate-digest ALLOWS entitled subscriber (repeat) and returns a cited digest', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK'; delete process.env.DIGEST_DEV_UNLOCK;
  await store._reset();
  await store.setPaid('email:buyer@example.com', { tier: 'monthly' });
  let res = makeRes();
  await load('api/generate-digest.js')({ method: 'POST', body: Object.assign({ email: 'Buyer@Example.com' }, REQUEST), headers: {} }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.ok, true);
  assert.strictEqual(res.body.coverage_pct, 100);
  assert.ok(res.body.markdown.includes('What changed'));
  // Repeat generation succeeds (subscription).
  res = makeRes();
  await load('api/generate-digest.js')({ method: 'POST', body: Object.assign({ email: 'Buyer@Example.com' }, REQUEST), headers: {} }, res);
  assert.strictEqual(res.statusCode, 200);
});

test('generate-digest returns 422 (fail-closed) on an uncited claim', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK'; delete process.env.DIGEST_DEV_UNLOCK;
  await store._reset();
  await store.setPaid('email:buyer@example.com', { tier: 'monthly' });
  const bad = JSON.parse(JSON.stringify(REQUEST));
  bad.changes.push({ text: 'uncited claim', citations: [] });
  const res = makeRes();
  await load('api/generate-digest.js')({ method: 'POST', body: Object.assign({ email: 'buyer@example.com' }, bad), headers: {} }, res);
  assert.strictEqual(res.statusCode, 422);
  assert.strictEqual(res.body.error, 'DIGEST_LINT_FAILED');
});

test('END-TO-END: checkout -> webhook grant -> entitled digest', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK'; process.env.STRIPE_WEBHOOK_SECRET = 'whsec_MOCK'; process.env.STRIPE_PRICE_MONTHLY = 'price_MOCK';
  delete process.env.DIGEST_DEV_UNLOCK;
  await store._reset();
  const EMAIL = 'e2e@example.com';

  let res = makeRes();
  await load('api/create-checkout-session.js')({ method: 'POST', body: { tier: 'monthly' }, headers: { origin: 'https://example.test' } }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.ok(res.body.url);

  res = makeRes();
  await load('api/generate-digest.js')({ method: 'POST', body: Object.assign({ email: EMAIL }, REQUEST), headers: {} }, res);
  assert.strictEqual(res.statusCode, 402);

  currentEvent = { type: 'checkout.session.completed', data: { object: { id: 'cs_e2e', mode: 'subscription', customer_details: { email: EMAIL }, customer: 'cus_e2e' } } };
  res = makeRes();
  await load('api/webhook.js')(rawReq('{}', { 'stripe-signature': 'good' }), res);
  assert.strictEqual(res.statusCode, 200);

  res = makeRes();
  await load('api/generate-digest.js')({ method: 'POST', body: Object.assign({ email: EMAIL }, REQUEST), headers: {} }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.ok, true);
});
