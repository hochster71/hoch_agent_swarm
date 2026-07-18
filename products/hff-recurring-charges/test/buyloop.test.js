// test/buyloop.test.js
//
// HFF — Recurring Charge Finder — buy-loop verification with node:test.
//
// SCOPE / HONESTY: LOGIC-LEVEL, TEST-MODE verification. Stripe is MOCKED (the
// `stripe` package is never called, no network, no keys) and the entitlement
// store runs on its in-memory fallback (no Vercel KV). It proves the code paths
// checkout -> signed webhook -> entitlement -> gated delivery are coherent.
// It is NOT a live run and NOT a real Stripe test-mode run.
//
// Run:  node test/buyloop.test.js
'use strict';

const test = require('node:test');
const assert = require('node:assert');
const Module = require('node:module');
const path = require('node:path');
const fs = require('node:fs');
const { Readable } = require('node:stream');

const ROOT = path.resolve(__dirname, '..');
const SAMPLE = fs.readFileSync(path.join(ROOT, 'engine', 'sample', 'sample_transactions.csv'), 'utf8');

let currentEvent = null;
let sessionPaid = true;

function makeFakeStripe() {
  return function Stripe(_key, _cfg) {
    return {
      checkout: {
        sessions: {
          create: async () => ({ id: 'cs_mock', url: 'https://checkout.stripe.com/pay/cs_mock' }),
          retrieve: async (id) => ({
            id,
            payment_status: sessionPaid ? 'paid' : 'unpaid',
            status: sessionPaid ? 'complete' : 'open',
          }),
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

// ------------------------------------------------------------------ checkout
test('checkout returns 501 when STRIPE_SECRET_KEY is absent (inert, not broken)', async () => {
  delete process.env.STRIPE_SECRET_KEY;
  const res = makeRes();
  await (load('api/create-checkout-session.js'))({ method: 'POST', body: { tier: 'report' }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 501);
  assert.strictEqual(res.body.error, 'not_configured');
});

test('checkout returns 501 when the price ID is absent', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  delete process.env.STRIPE_PRICE_REPORT;
  const res = makeRes();
  await (load('api/create-checkout-session.js'))({ method: 'POST', body: { tier: 'report' }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 501);
  assert.strictEqual(res.body.error, 'price_not_configured');
});

test('checkout rejects an unknown tier', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  process.env.STRIPE_PRICE_REPORT = 'price_MOCK';
  const res = makeRes();
  await (load('api/create-checkout-session.js'))({ method: 'POST', body: { tier: 'enterprise' }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 400);
  assert.strictEqual(res.body.error, 'invalid_tier');
});

// ------------------------------------------------------------------- webhook
test('webhook returns 501 when unconfigured (no keys)', async () => {
  delete process.env.STRIPE_SECRET_KEY;
  delete process.env.STRIPE_WEBHOOK_SECRET;
  const res = makeRes();
  await (load('api/webhook.js'))(rawReq('{}', { 'stripe-signature': 'good' }), res);
  assert.strictEqual(res.statusCode, 501);
  assert.strictEqual(res.body.error, 'not_configured');
});

test('webhook rejects a bad signature with 400 (fails closed)', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  process.env.STRIPE_WEBHOOK_SECRET = 'whsec_MOCK_NOT_REAL';
  currentEvent = null;
  const res = makeRes();
  await (load('api/webhook.js'))(rawReq('{}', { 'stripe-signature': 'bad' }), res);
  assert.strictEqual(res.statusCode, 400);
  assert.strictEqual(res.body.error, 'invalid_signature');
});

test('webhook writes a one-time entitlement on checkout.session.completed', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  process.env.STRIPE_WEBHOOK_SECRET = 'whsec_MOCK_NOT_REAL';
  await store._reset();
  currentEvent = {
    type: 'checkout.session.completed',
    data: { object: { id: 'cs_test_123', mode: 'payment', metadata: { product: 'hff-recurring-charges', tier: 'report' }, customer_details: { email: 'b@example.com' } } },
  };
  const res = makeRes();
  await (load('api/webhook.js'))(rawReq(JSON.stringify({ ok: 1 }), { 'stripe-signature': 'good' }), res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(await store.isPaid('sess:cs_test_123'), true);
});

test('webhook ignores an unrelated event without granting anything', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  process.env.STRIPE_WEBHOOK_SECRET = 'whsec_MOCK_NOT_REAL';
  await store._reset();
  currentEvent = { type: 'invoice.paid', data: { object: { id: 'in_1' } } };
  const res = makeRes();
  await (load('api/webhook.js'))(rawReq('{}', { 'stripe-signature': 'good' }), res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(await store.isPaid('sess:in_1'), false);
});

// --------------------------------------------------------------- entitlement
test('entitlement route returns { paid:true } for a granted session', async () => {
  await store._reset();
  await store.setPaid('sess:cs_abc', { tier: 'report' });
  const res = makeRes();
  await (load('api/entitlement.js'))({ method: 'GET', query: { session_id: 'cs_abc' } }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.paid, true);
});

test('entitlement route returns { paid:false } for an unknown session', async () => {
  await store._reset();
  const res = makeRes();
  await (load('api/entitlement.js'))({ method: 'GET', query: { session_id: 'cs_unknown' } }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.paid, false);
});

// -------------------------------------------------------------- free preview
test('free preview is NOT gated and returns real numbers with the paid part withheld', async () => {
  delete process.env.STRIPE_SECRET_KEY;
  await store._reset();
  const res = makeRes();
  await (load('api/preview.js'))({ method: 'POST', body: { csv: SAMPLE }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.ok, true);
  assert.ok(res.body.counts.recurringPatterns > 0);
  assert.ok(res.body.totals.annualized > 0);
  assert.strictEqual(res.body.sampleMerchants.length, 3, 'only a 3-row taste');
  assert.strictEqual(res.body.report, undefined, 'no full report in the preview');
  assert.strictEqual(res.body.files, undefined, 'no artifacts in the preview');
  assert.ok(res.body.disclaimer.includes('not financial, tax, or legal advice'));
});

test('preview surfaces an honest error for an unreadable file', async () => {
  const res = makeRes();
  await (load('api/preview.js'))({ method: 'POST', body: { csv: 'foo,bar\n1,2\n' }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 400);
  assert.strictEqual(res.body.error, 'MISSING_COLUMNS');
});

// ------------------------------------------------------------ gated delivery
test('generate-report DENIES an un-entitled request (402 when Stripe configured)', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  delete process.env.RECURRING_DEV_UNLOCK;
  await store._reset();
  sessionPaid = false;
  const res = makeRes();
  await (load('api/generate-report.js'))({ method: 'POST', body: { session_id: 'cs_unpaid', csv: SAMPLE }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 402);
  assert.strictEqual(res.body.error, 'not_entitled');
  sessionPaid = true;
});

test('generate-report DENIES with 501 when totally unconfigured', async () => {
  delete process.env.STRIPE_SECRET_KEY;
  delete process.env.RECURRING_DEV_UNLOCK;
  await store._reset();
  const res = makeRes();
  await (load('api/generate-report.js'))({ method: 'POST', body: { session_id: 'cs_x', csv: SAMPLE }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 501);
  assert.strictEqual(res.body.error, 'not_entitled');
});

test('generate-report ALLOWS an entitled session and returns both artifacts', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  delete process.env.RECURRING_DEV_UNLOCK;
  await store._reset();
  await store.setPaid('sess:cs_paid', { tier: 'report' });
  const res = makeRes();
  await (load('api/generate-report.js'))({ method: 'POST', body: { session_id: 'cs_paid', csv: SAMPLE }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.ok, true);
  assert.strictEqual(res.body.entitled_via, 'store');
  assert.ok(res.body.report.recurring.length > 0);
  const xlsx = Buffer.from(res.body.files.xlsx.base64, 'base64');
  const pdf = Buffer.from(res.body.files.pdf.base64, 'base64');
  assert.strictEqual(xlsx.slice(0, 2).toString(), 'PK');
  assert.strictEqual(pdf.slice(0, 5).toString(), '%PDF-');
  assert.strictEqual(xlsx.length, res.body.files.xlsx.bytes);
});

test('generate-report ALLOWS on a fresh paid session_id (verified with Stripe)', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  delete process.env.RECURRING_DEV_UNLOCK;
  await store._reset();
  sessionPaid = true;
  const res = makeRes();
  await (load('api/generate-report.js'))({ method: 'POST', body: { session_id: 'cs_fresh', csv: SAMPLE }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.entitled_via, 'session');
});

test('an entitled request with a poisoned file still fails CLOSED on the advice linter (422)', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  await store._reset();
  await store.setPaid('sess:cs_poison', { tier: 'report' });
  const bad = 'Date,Description,Amount\n' +
    '2026-01-01,"ACME (we recommend you cancel this)",10.00\n' +
    '2026-02-01,"ACME (we recommend you cancel this)",10.00\n' +
    '2026-03-01,"ACME (we recommend you cancel this)",10.00\n';
  const res = makeRes();
  await (load('api/generate-report.js'))({ method: 'POST', body: { session_id: 'cs_poison', csv: bad }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 422);
  assert.strictEqual(res.body.error, 'ADVICE_LINTER_FAILED');
  assert.strictEqual(res.body.files, undefined, 'paying does not buy past the guardrail');
});

// ----------------------------------------------------------------- END-TO-END
test('END-TO-END: checkout -> signed webhook grant -> entitled report (all mocked/in-memory)', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  process.env.STRIPE_WEBHOOK_SECRET = 'whsec_MOCK_NOT_REAL';
  process.env.STRIPE_PRICE_REPORT = 'price_MOCK';
  delete process.env.RECURRING_DEV_UNLOCK;
  await store._reset();
  sessionPaid = false; // force reliance on the webhook-written grant, not a live retrieve

  // 1. Checkout session created (mocked).
  let res = makeRes();
  await (load('api/create-checkout-session.js'))({ method: 'POST', body: { tier: 'report' }, headers: { origin: 'https://example.test' } }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.ok(res.body.url);

  // 2. Before payment, the report is denied.
  res = makeRes();
  await (load('api/generate-report.js'))({ method: 'POST', body: { session_id: 'cs_e2e', csv: SAMPLE }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 402);

  // 3. Stripe fires a SIGNED checkout.session.completed -> webhook writes the grant.
  currentEvent = { type: 'checkout.session.completed', data: { object: { id: 'cs_e2e', mode: 'payment', metadata: { tier: 'report' }, customer_details: { email: 'e2e@example.com' } } } };
  res = makeRes();
  await (load('api/webhook.js'))(rawReq('{}', { 'stripe-signature': 'good' }), res);
  assert.strictEqual(res.statusCode, 200);

  // 4. The entitlement route now reports paid.
  res = makeRes();
  await (load('api/entitlement.js'))({ method: 'GET', query: { session_id: 'cs_e2e' } }, res);
  assert.strictEqual(res.body.paid, true);

  // 5. And that session can generate the full report with both artifacts.
  res = makeRes();
  await (load('api/generate-report.js'))({ method: 'POST', body: { session_id: 'cs_e2e', csv: SAMPLE }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.ok, true);
  assert.ok(Buffer.from(res.body.files.pdf.base64, 'base64').slice(0, 5).toString() === '%PDF-');
  sessionPaid = true;
});
