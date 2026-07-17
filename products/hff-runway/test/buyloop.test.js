// test/buyloop.test.js
//
// HFF Runway — buy-loop verification with node:test.
//
// SCOPE / HONESTY: this is a LOGIC-LEVEL, TEST-MODE verification. Stripe is
// MOCKED (no `stripe` package call, no network, no keys) and the entitlement
// store runs on its in-memory fallback (no Vercel KV). It proves the code paths
// of checkout -> signed webhook -> entitlement -> gated packet generation are
// coherent. It is NOT a live run and NOT a real Stripe test-mode run (which
// would need founder keys + network).
//
// Run:  node test/buyloop.test.js       (node:test auto-runs)

'use strict';

const test = require('node:test');
const assert = require('node:assert');
const Module = require('node:module');
const path = require('node:path');
const { Readable } = require('node:stream');

const ROOT = path.resolve(__dirname, '..');

// ---------------------------------------------------------------------------
// Mock external modules ('stripe', '@vercel/kv') at the loader level so the
// code-under-test can `require('stripe')` WITHOUT hitting the network, and the
// store is forced onto its in-memory fallback.
// ---------------------------------------------------------------------------
let currentEvent = null;    // event returned by mocked webhooks.constructEvent
let sessionPaid = true;     // payment_status for mocked session retrieve

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
        // Only accepts the sentinel signature 'good'; everything else throws,
        // exactly like the real SDK on a bad signature.
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

// Shared store instance (same absolute path the api/* modules require).
const store = require(path.join(ROOT, 'lib', 'store.js'));

// A minimal-but-valid transactions CSV the engine accepts.
const SAMPLE_CSV = [
  'Date,Description,Amount',
  '2026-04-05,Client ACME Corp invoice 1001,8200.00',
  '2026-04-09,Upwork contractor Jane Dev,-1500.00',
  '2026-04-12,GitHub monthly subscription,-21.00',
  '2026-04-20,Office supplies,-88.40',
].join('\n');

// ---- tiny req/res helpers -------------------------------------------------
function makeRes() {
  const res = { statusCode: 200, body: null, headers: {} };
  res.status = (c) => { res.statusCode = c; return res; };
  res.json = (o) => { res.body = o; return res; };
  res.setHeader = (k, v) => { res.headers[k] = v; };
  return res;
}
function load(rel) {
  const p = require.resolve(path.join(ROOT, rel));
  delete require.cache[p]; // fresh handler each time (picks up env changes)
  return require(p);
}
function rawReq(bodyStr, headers) {
  const req = Readable.from([Buffer.from(bodyStr)]);
  req.method = 'POST';
  req.headers = headers || {};
  return req;
}

// ===========================================================================
// (a) webhook: rejects bad signature; writes entitlement on valid event
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

test('webhook writes entitlement on a valid checkout.session.completed', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  process.env.STRIPE_WEBHOOK_SECRET = 'whsec_MOCK_NOT_REAL';
  await store._reset();
  currentEvent = {
    type: 'checkout.session.completed',
    data: {
      object: {
        id: 'cs_test_123',
        mode: 'subscription',
        metadata: { product: 'hff-runway', tier: 'monthly' },
        customer_details: { email: 'Buyer@Example.com' },
        customer: 'cus_abc',
      },
    },
  };
  const handler = load('api/webhook.js');
  const res = makeRes();
  await handler(rawReq(JSON.stringify({ ok: 1 }), { 'stripe-signature': 'good' }), res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.received, true);
  // Entitlement written, email lowercased.
  assert.strictEqual(await store.isPaid('email:buyer@example.com'), true);
  // Customer -> email map written for later revoke.
  const map = await store.get('cust:cus_abc');
  assert.strictEqual(map && map.email, 'Buyer@Example.com');
});

test('webhook revokes on customer.subscription.deleted', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  process.env.STRIPE_WEBHOOK_SECRET = 'whsec_MOCK_NOT_REAL';
  await store._reset();
  await store.setPaid('email:buyer@example.com', { tier: 'monthly' });
  await store.put('cust:cus_abc', { email: 'buyer@example.com' });
  currentEvent = { type: 'customer.subscription.deleted', data: { object: { customer: 'cus_abc' } } };
  const handler = load('api/webhook.js');
  const res = makeRes();
  await handler(rawReq('{}', { 'stripe-signature': 'good' }), res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(await store.isPaid('email:buyer@example.com'), false);
});

// ===========================================================================
// (b) entitlement route reflects the webhook-written grant
// ===========================================================================
test('entitlement route returns { paid:true } for a granted email', async () => {
  await store._reset();
  await store.setPaid('email:buyer@example.com', { tier: 'monthly' });
  const handler = load('api/entitlement.js');
  const res = makeRes();
  await handler({ method: 'GET', query: { email: 'Buyer@Example.com' } }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.paid, true);
  assert.strictEqual(res.body.tier, 'monthly');
});

test('entitlement route returns { paid:false } for an unknown email', async () => {
  await store._reset();
  const handler = load('api/entitlement.js');
  const res = makeRes();
  await handler({ method: 'GET', query: { email: 'nobody@example.com' } }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.paid, false);
});

// ===========================================================================
// (c) generate-packet gate: allows entitled subscriber, denies un-entitled
// ===========================================================================
test('generate-packet DENIES an un-entitled request (402 when Stripe configured)', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  delete process.env.RUNWAY_DEV_UNLOCK;
  await store._reset();
  const handler = load('api/generate-packet.js');
  const res = makeRes();
  await handler({ method: 'POST', body: { email: 'nobody@example.com', csv: SAMPLE_CSV }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 402);
  assert.strictEqual(res.body.error, 'not_entitled');
});

test('generate-packet DENIES with 501 when totally unconfigured (no key, no dev unlock)', async () => {
  delete process.env.STRIPE_SECRET_KEY;
  delete process.env.RUNWAY_DEV_UNLOCK;
  await store._reset();
  const handler = load('api/generate-packet.js');
  const res = makeRes();
  await handler({ method: 'POST', body: { email: 'nobody@example.com', csv: SAMPLE_CSV }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 501);
  assert.strictEqual(res.body.error, 'not_entitled');
});

test('generate-packet ALLOWS an entitled subscriber (repeat generation by email)', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  delete process.env.RUNWAY_DEV_UNLOCK;
  await store._reset();
  await store.setPaid('email:buyer@example.com', { tier: 'monthly' });
  const handler = load('api/generate-packet.js');

  // First generation.
  let res = makeRes();
  await handler({ method: 'POST', body: { email: 'Buyer@Example.com', csv: SAMPLE_CSV }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.ok, true);
  assert.ok(res.body.files.xlsxBase64 && res.body.files.pdfBase64, 'expected packet file bytes');

  // Repeat generation succeeds too (subscription, not one-shot).
  res = makeRes();
  await handler({ method: 'POST', body: { email: 'Buyer@Example.com', csv: SAMPLE_CSV }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.ok, true);
});

test('generate-packet ALLOWS on a fresh paid session_id (first run right after checkout)', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  delete process.env.RUNWAY_DEV_UNLOCK;
  await store._reset();
  sessionPaid = true;
  const handler = load('api/generate-packet.js');
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
  process.env.STRIPE_PRICE_MONTHLY = 'price_MOCK';
  delete process.env.RUNWAY_DEV_UNLOCK;
  await store._reset();
  const EMAIL = 'e2e@example.com';

  // 1. Checkout session created (mocked stripe returns a url).
  let res = makeRes();
  await (load('api/create-checkout-session.js'))(
    { method: 'POST', body: { tier: 'monthly' }, headers: { origin: 'https://example.test' } },
    res
  );
  assert.strictEqual(res.statusCode, 200);
  assert.ok(res.body.url);

  // 2. Before payment, an entitled generate is denied.
  res = makeRes();
  await (load('api/generate-packet.js'))({ method: 'POST', body: { email: EMAIL, csv: SAMPLE_CSV }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 402);

  // 3. Stripe fires a SIGNED checkout.session.completed -> webhook writes grant.
  currentEvent = {
    type: 'checkout.session.completed',
    data: { object: {
      id: 'cs_e2e', mode: 'subscription', metadata: { product: 'hff-runway', tier: 'monthly' },
      customer_details: { email: EMAIL }, customer: 'cus_e2e',
    } },
  };
  res = makeRes();
  await (load('api/webhook.js'))(rawReq('{}', { 'stripe-signature': 'good' }), res);
  assert.strictEqual(res.statusCode, 200);

  // 4. Now the same email can generate a packet.
  res = makeRes();
  await (load('api/generate-packet.js'))({ method: 'POST', body: { email: EMAIL, csv: SAMPLE_CSV }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.ok, true);
});
