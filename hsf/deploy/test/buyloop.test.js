// test/buyloop.test.js
//
// HSF Story Studio — buy-loop verification with node:test.
//
// SCOPE / HONESTY: this is a LOGIC-LEVEL, TEST-MODE verification. Stripe is
// MOCKED (no `stripe` package, no network, no keys) and the entitlement store
// runs on its in-memory fallback (no Vercel KV). It proves the code paths of
// checkout -> signed webhook -> entitlement are coherent. It is NOT a live run
// and NOT a real Stripe test-mode run (which would need founder keys + network).
//
// Run:  cd hsf/deploy && node --test

'use strict';

const test = require('node:test');
const assert = require('node:assert');
const Module = require('node:module');
const path = require('node:path');
const { Readable } = require('node:stream');

const DEPLOY = path.resolve(__dirname, '..');

// ---------------------------------------------------------------------------
// Mock external modules ('stripe', '@vercel/kv') at the loader level so the
// code-under-test can `require('stripe')` WITHOUT the package being installed.
// ---------------------------------------------------------------------------
let currentEvent = null;   // event returned by mocked webhooks.constructEvent
let stripeInstalled = true; // toggle to simulate the package being absent

function makeFakeStripe() {
  return function Stripe(_key, _cfg) {
    return {
      paymentLinks: {
        list: async () => ({ data: [] }),
        create: async () => ({ id: 'plink_mock', url: 'https://checkout.stripe.com/pay/mock_link' }),
      },
      checkout: {
        sessions: {
          create: async () => ({ id: 'cs_mock', url: 'https://checkout.stripe.com/pay/cs_mock' }),
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
Module._load = function (request, parent, isMain) {
  if (request === 'stripe') {
    if (!stripeInstalled) {
      const e = new Error("Cannot find module 'stripe'");
      e.code = 'MODULE_NOT_FOUND';
      throw e;
    }
    return makeFakeStripe();
  }
  if (request === '@vercel/kv') {
    // Force the store's in-memory fallback path even if env were set.
    const e = new Error("Cannot find module '@vercel/kv'");
    e.code = 'MODULE_NOT_FOUND';
    throw e;
  }
  return origLoad.apply(this, arguments);
};

// Shared store instance (same absolute path the api/* modules require).
const store = require(path.join(DEPLOY, 'lib', 'store.js'));

// ---- tiny req/res helpers -------------------------------------------------
function makeRes() {
  const res = { statusCode: 200, body: null, headers: {} };
  res.status = (c) => { res.statusCode = c; return res; };
  res.json = (o) => { res.body = o; return res; };
  res.setHeader = (k, v) => { res.headers[k] = v; };
  return res;
}
function load(rel) {
  const p = require.resolve(path.join(DEPLOY, rel));
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
// (a) create-checkout-session: safe default vs mocked-key behaviour
// ===========================================================================
test('create-checkout-session returns 501 not_configured when no STRIPE_SECRET_KEY', async () => {
  delete process.env.STRIPE_SECRET_KEY;
  const handler = load('api/create-checkout-session.js');
  const res = makeRes();
  await handler({ method: 'POST', body: { tier: 'onestory' }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 501);
  assert.strictEqual(res.body.error, 'not_configured');
});

test('create-checkout-session returns a checkout url when a key IS present (mocked Stripe)', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  process.env.STRIPE_PRICE_ONESTORY = 'price_MOCK';
  stripeInstalled = true;
  const handler = load('api/create-checkout-session.js');
  const res = makeRes();
  await handler(
    { method: 'POST', body: { tier: 'onestory', storyId: 'story-abc' }, headers: { origin: 'https://example.test' } },
    res
  );
  assert.strictEqual(res.statusCode, 200);
  assert.ok(res.body.url, 'expected a url in the response');
  assert.match(res.body.url, /checkout\.stripe\.com/);
});

// ===========================================================================
// (b) webhook: rejects bad signature; writes entitlement on valid event
// ===========================================================================
test('webhook rejects a bad signature with 400', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  process.env.STRIPE_WEBHOOK_SECRET = 'whsec_MOCK_NOT_REAL';
  currentEvent = null;
  const handler = load('api/webhook.js');
  const res = makeRes();
  await handler(rawReq('{}', { 'stripe-signature': 'bad' }), res);
  assert.strictEqual(res.statusCode, 400);
  assert.strictEqual(res.body.error, 'invalid_signature');
});

test('webhook returns 501 when unconfigured (no keys)', async () => {
  delete process.env.STRIPE_SECRET_KEY;
  delete process.env.STRIPE_WEBHOOK_SECRET;
  const handler = load('api/webhook.js');
  const res = makeRes();
  await handler(rawReq('{}', { 'stripe-signature': 'good' }), res);
  assert.strictEqual(res.statusCode, 501);
  assert.strictEqual(res.body.error, 'not_configured');
});

test('webhook writes an entitlement on a valid checkout.session.completed', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  process.env.STRIPE_WEBHOOK_SECRET = 'whsec_MOCK_NOT_REAL';
  await store._reset();
  currentEvent = {
    type: 'checkout.session.completed',
    data: {
      object: {
        id: 'cs_test_123',
        mode: 'payment',
        client_reference_id: 'story-xyz',
        metadata: { tier: 'onestory' },
        customer_details: { email: 'buyer@example.com' },
        customer: null,
      },
    },
  };
  const handler = load('api/webhook.js');
  const res = makeRes();
  await handler(rawReq(JSON.stringify({ ok: 1 }), { 'stripe-signature': 'good' }), res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.received, true);
  assert.strictEqual(await store.isPaid('story:story-xyz'), true);
});

// ===========================================================================
// (c) entitlement route reads the entitlement true after the webhook grant
// ===========================================================================
test('entitlement route returns { paid:true } for a granted story', async () => {
  await store._reset();
  await store.setPaid('story:story-xyz', { tier: 'onestory', sessionId: 'cs_test_123' });
  const handler = load('api/entitlement.js');
  const res = makeRes();
  await handler({ method: 'GET', query: { storyId: 'story-xyz' } }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.paid, true);
  assert.strictEqual(res.body.tier, 'onestory');
});

test('entitlement route returns { paid:false } for an unknown story', async () => {
  await store._reset();
  const handler = load('api/entitlement.js');
  const res = makeRes();
  await handler({ method: 'GET', query: { storyId: 'never-paid' } }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.paid, false);
});

// ===========================================================================
// creators subscription path: setPaid(email) + cust: map, revoke on cancel
// ===========================================================================
test('creators subscription: webhook grants by email, revoke on subscription.deleted', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  process.env.STRIPE_WEBHOOK_SECRET = 'whsec_MOCK_NOT_REAL';
  await store._reset();

  // Grant via checkout.session.completed (creators tier).
  currentEvent = {
    type: 'checkout.session.completed',
    data: { object: {
      id: 'cs_sub_1', mode: 'subscription', metadata: { tier: 'creators' },
      customer_details: { email: 'Creator@Example.com' }, customer: 'cus_123',
    } },
  };
  let handler = load('api/webhook.js');
  await handler(rawReq('{}', { 'stripe-signature': 'good' }), makeRes());
  assert.strictEqual(await store.isPaid('email:creator@example.com'), true);

  // Revoke via customer.subscription.deleted (uses cust: -> email map).
  currentEvent = { type: 'customer.subscription.deleted', data: { object: { customer: 'cus_123' } } };
  handler = load('api/webhook.js');
  await handler(rawReq('{}', { 'stripe-signature': 'good' }), makeRes());
  assert.strictEqual(await store.isPaid('email:creator@example.com'), false);
});

// ===========================================================================
// STUB gate: export returns 402 unpaid, 501(stub) once entitled
// ===========================================================================
test('export STUB: 402 when unpaid, 501 not_implemented(stub) once entitled', async () => {
  await store._reset();
  const handler = load('api/export.js');

  let res = makeRes();
  await handler({ method: 'POST', body: { storyId: 's1' }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 402);
  assert.strictEqual(res.body.error, 'payment_required');

  await store.setPaid('story:s1', { tier: 'onestory' });
  res = makeRes();
  await handler({ method: 'POST', body: { storyId: 's1' }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 501);
  assert.strictEqual(res.body.stub, true);
});

// ===========================================================================
// End-to-end: checkout(mocked) -> webhook grant -> entitlement flips true
// ===========================================================================
test('END-TO-END loop: checkout -> webhook -> entitlement true (all mocked/in-memory)', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  process.env.STRIPE_WEBHOOK_SECRET = 'whsec_MOCK_NOT_REAL';
  process.env.STRIPE_PRICE_ONESTORY = 'price_MOCK';
  await store._reset();
  const STORY = 'e2e-story-001';

  // 1. checkout session created (mocked stripe returns a url)
  let res = makeRes();
  await (load('api/create-checkout-session.js'))(
    { method: 'POST', body: { tier: 'onestory', storyId: STORY }, headers: { origin: 'https://example.test' } },
    res
  );
  assert.strictEqual(res.statusCode, 200);
  assert.ok(res.body.url);

  // 2. before payment, entitlement is false
  res = makeRes();
  await (load('api/entitlement.js'))({ method: 'GET', query: { storyId: STORY } }, res);
  assert.strictEqual(res.body.paid, false);

  // 3. Stripe fires signed checkout.session.completed -> webhook writes grant
  currentEvent = {
    type: 'checkout.session.completed',
    data: { object: {
      id: 'cs_e2e', mode: 'payment', client_reference_id: STORY,
      metadata: { tier: 'onestory' }, customer_details: { email: 'e2e@example.com' }, customer: null,
    } },
  };
  res = makeRes();
  await (load('api/webhook.js'))(rawReq('{}', { 'stripe-signature': 'good' }), res);
  assert.strictEqual(res.statusCode, 200);

  // 4. entitlement now true
  res = makeRes();
  await (load('api/entitlement.js'))({ method: 'GET', query: { storyId: STORY } }, res);
  assert.strictEqual(res.body.paid, true);
});
