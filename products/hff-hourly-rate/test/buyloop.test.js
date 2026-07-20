// test/buyloop.test.js
//
// HFF — Effective Hourly Rate Report — buy-loop verification with node:test.
//
// SCOPE / HONESTY: LOGIC-LEVEL verification only. Stripe is MOCKED (the `stripe`
// package is never really loaded, no network, no keys) and the entitlement store
// runs on its in-memory fallback (no Vercel KV). It proves the code paths
// checkout -> signed webhook -> entitlement -> gated delivery are coherent and
// fail closed. It is NOT a live run and NOT a real Stripe test-mode run.
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
const SAMPLE = fs.readFileSync(path.join(ROOT, 'engine', 'sample', 'sample_timesheet.csv'), 'utf8');

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
function clearEnv() {
  delete process.env.STRIPE_SECRET_KEY;
  delete process.env.STRIPE_PRICE_REPORT;
  delete process.env.STRIPE_WEBHOOK_SECRET;
  delete process.env.HOURLYRATE_DEV_UNLOCK;
}

// =================================================================== checkout

test('checkout is INERT (501) with no STRIPE_SECRET_KEY — not broken, not fake', async () => {
  clearEnv();
  const res = makeRes();
  await (load('api/create-checkout-session.js'))({ method: 'POST', body: { tier: 'report' }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 501);
  assert.strictEqual(res.body.error, 'not_configured');
});

test('checkout is INERT (501) when the price ID is missing', async () => {
  clearEnv();
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  const res = makeRes();
  await (load('api/create-checkout-session.js'))({ method: 'POST', body: { tier: 'report' }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 501);
  assert.strictEqual(res.body.error, 'price_not_configured');
});

test('checkout rejects an unknown tier with 400', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  process.env.STRIPE_PRICE_REPORT = 'price_MOCK';
  const res = makeRes();
  await (load('api/create-checkout-session.js'))({ method: 'POST', body: { tier: 'enterprise' }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 400);
  assert.strictEqual(res.body.error, 'invalid_tier');
});

test('checkout rejects a non-POST method with 405 and an Allow header', async () => {
  const res = makeRes();
  await (load('api/create-checkout-session.js'))({ method: 'GET', headers: {} }, res);
  assert.strictEqual(res.statusCode, 405);
  assert.strictEqual(res.headers.Allow, 'POST');
});

test('checkout returns a hosted URL once keys and price are present (mocked Stripe)', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  process.env.STRIPE_PRICE_REPORT = 'price_MOCK';
  process.env.BASE_URL = 'https://example.test';
  const res = makeRes();
  await (load('api/create-checkout-session.js'))({ method: 'POST', body: { tier: 'report' }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.match(res.body.url, /^https:\/\/checkout\.stripe\.com\//);
});

test('checkout handles a malformed JSON string body with 400, not a crash', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  process.env.STRIPE_PRICE_REPORT = 'price_MOCK';
  const res = makeRes();
  await (load('api/create-checkout-session.js'))({ method: 'POST', body: '{not json', headers: {} }, res);
  assert.strictEqual(res.statusCode, 400);
  assert.strictEqual(res.body.error, 'bad_json');
});

// ==================================================================== webhook

test('webhook is INERT (501) when unconfigured', async () => {
  clearEnv();
  const res = makeRes();
  await (load('api/webhook.js'))(rawReq('{}', { 'stripe-signature': 'good' }), res);
  assert.strictEqual(res.statusCode, 501);
  assert.strictEqual(res.body.error, 'not_configured');
});

test('webhook REJECTS a bad signature with 400 (fails closed)', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  process.env.STRIPE_WEBHOOK_SECRET = 'whsec_MOCK';
  currentEvent = { type: 'checkout.session.completed', data: { object: { id: 'cs_evil' } } };
  const res = makeRes();
  await (load('api/webhook.js'))(rawReq('{}', { 'stripe-signature': 'forged' }), res);
  assert.strictEqual(res.statusCode, 400);
  assert.strictEqual(res.body.error, 'invalid_signature');
  assert.strictEqual(await store.isPaid('sess:cs_evil'), false, 'a forged event must NEVER grant entitlement');
});

test('webhook rejects a missing signature header with 400', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  process.env.STRIPE_WEBHOOK_SECRET = 'whsec_MOCK';
  const res = makeRes();
  await (load('api/webhook.js'))(rawReq('{}', {}), res);
  assert.strictEqual(res.statusCode, 400);
});

test('webhook GRANTS entitlement on a signed checkout.session.completed', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  process.env.STRIPE_WEBHOOK_SECRET = 'whsec_MOCK';
  currentEvent = {
    type: 'checkout.session.completed',
    data: {
      object: {
        id: 'cs_paid_1', mode: 'payment',
        metadata: { tier: 'report' },
        customer_details: { email: 'buyer@example.test' },
      },
    },
  };
  const res = makeRes();
  await (load('api/webhook.js'))(rawReq('{}', { 'stripe-signature': 'good' }), res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.received, true);
  assert.strictEqual(await store.isPaid('sess:cs_paid_1'), true);
  const rec = await store.get('sess:cs_paid_1');
  assert.strictEqual(rec.product, 'hff-hourly-rate');
  assert.strictEqual(rec.email, 'buyer@example.test');
});

test('webhook ignores an unrelated signed event without granting anything', async () => {
  currentEvent = { type: 'invoice.paid', data: { object: { id: 'in_123' } } };
  const res = makeRes();
  await (load('api/webhook.js'))(rawReq('{}', { 'stripe-signature': 'good' }), res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(await store.isPaid('sess:in_123'), false);
});

test('REGRESSION: webhook exports config with bodyParser disabled', () => {
  // Some sibling products assign module.exports.config BEFORE replacing
  // module.exports with the handler, which silently drops the config and would
  // break EVERY signature verification in production. Guard against that here.
  const handler = load('api/webhook.js');
  assert.strictEqual(typeof handler, 'function', 'the module must export the handler itself');
  assert.ok(handler.config, 'config must survive the module.exports assignment');
  assert.strictEqual(handler.config.api.bodyParser, false);
});

// ================================================================ entitlement

test('entitlement reports false for an unknown session', async () => {
  const res = makeRes();
  await (load('api/entitlement.js'))({ method: 'GET', query: { session_id: 'cs_unknown' } }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.paid, false);
});

test('entitlement reports true for the session the webhook granted', async () => {
  const res = makeRes();
  await (load('api/entitlement.js'))({ method: 'GET', query: { session_id: 'cs_paid_1' } }, res);
  assert.strictEqual(res.body.paid, true);
  assert.strictEqual(res.body.source, 'session');
});

test('entitlement with no session_id returns false rather than erroring', async () => {
  const res = makeRes();
  await (load('api/entitlement.js'))({ method: 'GET', query: {} }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.paid, false);
});

// ============================================================ gated delivery

test('report generation is INERT (501) with no keys and no dev unlock', async () => {
  clearEnv();
  const res = makeRes();
  await (load('api/generate-report.js'))({ method: 'POST', body: { csv: SAMPLE }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 501);
  assert.strictEqual(res.body.error, 'not_entitled');
});

test('report generation REFUSES (402) an unpaid session when Stripe is configured', async () => {
  clearEnv();
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  sessionPaid = false;
  const res = makeRes();
  await (load('api/generate-report.js'))(
    { method: 'POST', body: { csv: SAMPLE, session_id: 'cs_unpaid' }, headers: {} }, res
  );
  assert.strictEqual(res.statusCode, 402);
  assert.strictEqual(res.body.files, undefined, 'no artifacts may leak to an unpaid caller');
  sessionPaid = true;
});

test('report generation REFUSES (402) when Stripe is configured but no session is supplied', async () => {
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  const res = makeRes();
  await (load('api/generate-report.js'))({ method: 'POST', body: { csv: SAMPLE }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 402);
});

test('report generation DELIVERS for the entitled session (store path)', async () => {
  clearEnv();
  const res = makeRes();
  await (load('api/generate-report.js'))(
    { method: 'POST', body: { csv: SAMPLE, session_id: 'cs_paid_1' }, headers: {} }, res
  );
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.entitled_via, 'store');
  assert.ok(res.body.files.xlsx.bytes > 0 && res.body.files.pdf.bytes > 0);
  assert.strictEqual(
    Buffer.from(res.body.files.pdf.base64, 'base64').slice(0, 8).toString(), '%PDF-1.4'
  );
  assert.ok(Array.isArray(res.body.report.clients) && res.body.report.clients.length > 0);
  assert.ok(res.body.report.disclaimer.includes('not financial, tax, or legal advice'));
});

test('the delivered payload strips raw per-entry rows out of each client object', async () => {
  // Keeps the response lean and avoids shipping the same rows twice.
  // (Per-entry detail lives on the "All Entries" sheet of the workbook.)
  clearEnv();
  const res = makeRes();
  await (load('api/generate-report.js'))(
    { method: 'POST', body: { csv: SAMPLE, session_id: 'cs_paid_1' }, headers: {} }, res
  );
  assert.strictEqual(res.statusCode, 200);
  const clients = res.body.report.clients;
  assert.ok(clients.length > 0);
  for (const c of clients) {
    assert.strictEqual(c.rows, undefined, `client ${c.label} must not carry its raw rows`);
    assert.ok(typeof c.hours === 'number', 'the aggregate fields must survive the strip');
    assert.ok(typeof c.hoursSharePct === 'number');
  }
});

test('report generation DELIVERS via a Stripe-verified paid session', async () => {
  clearEnv();
  process.env.STRIPE_SECRET_KEY = 'sk_test_MOCK_NOT_REAL';
  sessionPaid = true;
  const res = makeRes();
  await (load('api/generate-report.js'))(
    { method: 'POST', body: { csv: SAMPLE, session_id: 'cs_verified_by_stripe' }, headers: {} }, res
  );
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.entitled_via, 'session');
});

test('DEV UNLOCK works locally and is labelled as dev, never as a real payment', async () => {
  clearEnv();
  process.env.HOURLYRATE_DEV_UNLOCK = '1';
  const res = makeRes();
  await (load('api/generate-report.js'))({ method: 'POST', body: { csv: SAMPLE }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.dev_unlock, true);
  assert.strictEqual(res.body.entitled_via, 'dev');
});

test('an entitled caller with a bad CSV gets an honest 400, not a fabricated report', async () => {
  process.env.HOURLYRATE_DEV_UNLOCK = '1';
  const res = makeRes();
  await (load('api/generate-report.js'))(
    { method: 'POST', body: { csv: 'Date,Notes\n2025-01-01,hi\n' }, headers: {} }, res
  );
  assert.strictEqual(res.statusCode, 400);
  assert.strictEqual(res.body.error, 'MISSING_COLUMNS');
  assert.strictEqual(res.body.files, undefined);
});

test('an entitled caller with an oversized file gets 413', async () => {
  process.env.HOURLYRATE_DEV_UNLOCK = '1';
  const res = makeRes();
  await (load('api/generate-report.js'))(
    { method: 'POST', body: { csv: 'Date,Client,Hours\n' + 'x\n'.repeat(50001) }, headers: {} }, res
  );
  assert.strictEqual(res.statusCode, 413);
});

test('an entitled caller with no CSV gets 400 no_csv', async () => {
  process.env.HOURLYRATE_DEV_UNLOCK = '1';
  const res = makeRes();
  await (load('api/generate-report.js'))({ method: 'POST', body: {}, headers: {} }, res);
  assert.strictEqual(res.statusCode, 400);
  assert.strictEqual(res.body.error, 'no_csv');
});

test('GUARDRAIL: the advice linter fails closed even for a PAYING caller (422, no files)', async () => {
  clearEnv();
  const enginePath = require.resolve(path.join(ROOT, 'engine', 'index.js'));
  const real = require(enginePath);
  const original = real.buildReport;
  // Simulate a regression in engine wording reaching a paid request.
  require.cache[enginePath].exports = Object.assign({}, real, {
    buildReport() {
      const e = new Error('ADVICE_LINTER_FAILED: banned advice language detected — report withheld.');
      e.code = 'ADVICE_LINTER_FAILED';
      throw e;
    },
  });
  try {
    const res = makeRes();
    await (load('api/generate-report.js'))(
      { method: 'POST', body: { csv: SAMPLE, session_id: 'cs_paid_1' }, headers: {} }, res
    );
    assert.strictEqual(res.statusCode, 422);
    assert.strictEqual(res.body.error, 'ADVICE_LINTER_FAILED');
    assert.strictEqual(res.body.files, undefined, 'a guardrail failure must withhold ALL artifacts');
  } finally {
    require.cache[enginePath].exports = Object.assign({}, real, { buildReport: original });
  }
});

test('report generation rejects a non-POST method with 405', async () => {
  const res = makeRes();
  await (load('api/generate-report.js'))({ method: 'GET', headers: {} }, res);
  assert.strictEqual(res.statusCode, 405);
});

// =============================================================== free preview

test('free preview works with NO keys and NO entitlement', async () => {
  clearEnv();
  const res = makeRes();
  await (load('api/preview.js'))({ method: 'POST', body: { csv: SAMPLE }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 200);
  assert.strictEqual(res.body.preview, true);
  assert.ok(res.body.hours.total > 0);
  assert.ok(res.body.topClients.length > 0);
});

test('free preview WITHHOLDS the paid artifacts and the full tables', async () => {
  const res = makeRes();
  await (load('api/preview.js'))({ method: 'POST', body: { csv: SAMPLE }, headers: {} }, res);
  assert.strictEqual(res.body.files, undefined, 'no XLSX/PDF may be returned for free');
  assert.strictEqual(res.body.monthly, undefined, 'the monthly series is paid-only');
  assert.strictEqual(res.body.weekdays, undefined, 'the weekday series is paid-only');
  assert.strictEqual(res.body.skipped, undefined, 'flagged-row detail is paid-only');
  assert.ok(res.body.topClients.length <= 3, 'preview shows at most three clients');
  assert.ok(res.body.withheld.includes('unlocked after purchase'));
});

test('free preview figures are a genuine SUBSET of the paid run, not a separate estimate', async () => {
  clearEnv();
  const pres = makeRes();
  await (load('api/preview.js'))({ method: 'POST', body: { csv: SAMPLE }, headers: {} }, pres);

  process.env.HOURLYRATE_DEV_UNLOCK = '1';
  const gres = makeRes();
  await (load('api/generate-report.js'))({ method: 'POST', body: { csv: SAMPLE }, headers: {} }, gres);

  assert.strictEqual(pres.body.hours.total, gres.body.report.summary.hours.total);
  assert.strictEqual(
    pres.body.rates.effectiveRateCovered,
    gres.body.report.summary.rates.effectiveRateCovered
  );
  assert.deepStrictEqual(pres.body.counts, gres.body.report.summary.counts);
});

test('free preview surfaces engine errors honestly instead of returning empty success', async () => {
  const res = makeRes();
  await (load('api/preview.js'))({ method: 'POST', body: { csv: 'Date,Notes\nx,y\n' }, headers: {} }, res);
  assert.strictEqual(res.statusCode, 400);
  assert.strictEqual(res.body.error, 'MISSING_COLUMNS');
});

// ================================================================== teardown

test('teardown: no real Stripe key was ever set by this suite', () => {
  const k = process.env.STRIPE_SECRET_KEY || '';
  assert.ok(k === '' || k.startsWith('sk_test_MOCK'), 'tests must never carry a live key');
  clearEnv();
  Module._load = origLoad;
});
