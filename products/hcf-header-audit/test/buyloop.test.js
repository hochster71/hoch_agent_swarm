// test/buyloop.test.js — HCF Email Header Audit — buy-loop tests.
//
// NO NETWORK, NO KEYS, NO STRIPE ACCOUNT. The `stripe` module is MOCKED via the
// require cache, and the entitlement store runs on its in-memory fallback.
// These prove the code paths are coherent and fail closed. They are NOT a live
// Stripe run and NOT proof that a real payment works.
'use strict';

const assert = require('assert');
const path = require('path');
const Module = require('module');

let pass = 0, fail = 0;
async function t(name, fn) {
  try { await fn(); pass += 1; console.log('  ok  ' + name); }
  catch (e) { fail += 1; console.error('  FAIL ' + name + '\n       ' + e.message); }
}

// ---- Stripe mock ---------------------------------------------------------
const mockState = { sessions: {}, created: [], constructShouldThrow: false, lastConstructArgs: null };
function StripeMock() {
  return {
    checkout: {
      sessions: {
        create: async (args) => {
          mockState.created.push(args);
          return { id: 'cs_test_mock', url: 'https://checkout.stripe.test/c/cs_test_mock' };
        },
        retrieve: async (id) => {
          if (!mockState.sessions[id]) { const e = new Error('No such session'); throw e; }
          return mockState.sessions[id];
        },
      },
    },
    webhooks: {
      constructEvent: (raw, sig, secret) => {
        mockState.lastConstructArgs = { raw, sig, secret };
        if (mockState.constructShouldThrow) throw new Error('signature mismatch');
        return JSON.parse(raw.toString('utf8'));
      },
    },
  };
}
require.cache[require.resolve('module')] = require.cache[require.resolve('module')];
const origResolve = Module._resolveFilename;
Module._resolveFilename = function (request, ...rest) {
  if (request === 'stripe') return 'STRIPE_MOCK';
  return origResolve.call(this, request, ...rest);
};
require.cache['STRIPE_MOCK'] = { id: 'STRIPE_MOCK', filename: 'STRIPE_MOCK', loaded: true, exports: StripeMock };

// ---- tiny res/req harness ------------------------------------------------
function mkRes() {
  const res = { statusCode: null, body: null, headers: {} };
  res.status = (c) => { res.statusCode = c; return res; };
  res.json = (b) => { res.body = b; return res; };
  res.setHeader = (k, v) => { res.headers[k] = v; };
  return res;
}
function mkReq(opts) {
  return Object.assign({ method: 'POST', headers: {}, query: {}, body: {} }, opts || {});
}
function mkRawReq(bodyString, headers) {
  const req = mkReq({ headers: headers || {} });
  req.on = (evt, cb) => {
    if (evt === 'data') process.nextTick(() => cb(Buffer.from(bodyString)));
    if (evt === 'end') process.nextTick(() => cb());
    return req;
  };
  return req;
}

const P = (f) => path.join(__dirname, '..', 'api', f);
const store = require('../lib/store');

function clearEnv() {
  delete process.env.STRIPE_SECRET_KEY;
  delete process.env.STRIPE_PRICE_AUDIT;
  delete process.env.STRIPE_WEBHOOK_SECRET;
  delete process.env.HEADER_DEV_UNLOCK;
  delete process.env.BASE_URL;
}

const SAMPLE_HEADERS = require('fs').readFileSync(
  path.join(__dirname, '..', 'engine', 'sample', 'sample_headers.txt'), 'utf8');

(async function run() {
  console.log('\nHCF Email Header Audit — buy-loop tests (stripe MOCKED, no keys, no network)\n');

  const checkout = require(P('create-checkout-session.js'));
  const webhook = require(P('webhook.js'));
  const entitlement = require(P('entitlement.js'));
  const generate = require(P('generate-report.js'));
  const preview = require(P('preview.js'));

  console.log('checkout');
  await t('is INERT (501) with no STRIPE_SECRET_KEY', async () => {
    clearEnv();
    const res = mkRes();
    await checkout(mkReq({ body: { tier: 'audit' } }), res);
    assert.strictEqual(res.statusCode, 501);
    assert.strictEqual(res.body.error, 'not_configured');
  });
  await t('is INERT (501) when the price ID is missing', async () => {
    clearEnv(); process.env.STRIPE_SECRET_KEY = 'sk_test_x';
    const res = mkRes();
    await checkout(mkReq({ body: { tier: 'audit' } }), res);
    assert.strictEqual(res.statusCode, 501);
    assert.strictEqual(res.body.error, 'price_not_configured');
  });
  await t('rejects a non-POST method', async () => {
    const res = mkRes();
    await checkout(mkReq({ method: 'GET' }), res);
    assert.strictEqual(res.statusCode, 405);
  });
  await t('rejects an unknown tier', async () => {
    clearEnv(); process.env.STRIPE_SECRET_KEY = 'sk_test_x'; process.env.STRIPE_PRICE_AUDIT = 'price_x';
    const res = mkRes();
    await checkout(mkReq({ body: { tier: 'enterprise' } }), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error, 'invalid_tier');
  });
  await t('creates a ONE-TIME payment session with the configured price', async () => {
    clearEnv();
    process.env.STRIPE_SECRET_KEY = 'sk_test_x';
    process.env.STRIPE_PRICE_AUDIT = 'price_audit_123';
    process.env.BASE_URL = 'https://audit.test';
    mockState.created.length = 0;
    const res = mkRes();
    await checkout(mkReq({ body: { tier: 'audit' } }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.ok(res.body.url.startsWith('https://checkout.stripe.test/'));
    const args = mockState.created[0];
    assert.strictEqual(args.mode, 'payment');
    assert.strictEqual(args.line_items[0].price, 'price_audit_123');
    assert.strictEqual(args.metadata.product, 'hcf-header-audit');
    assert.ok(args.success_url.includes('{CHECKOUT_SESSION_ID}'));
  });

  console.log('\nwebhook');
  await t('is INERT (501) with no keys', async () => {
    clearEnv();
    const res = mkRes();
    await webhook(mkRawReq('{}'), res);
    assert.strictEqual(res.statusCode, 501);
  });
  await t('FAILS CLOSED (400) on a bad signature', async () => {
    clearEnv();
    process.env.STRIPE_SECRET_KEY = 'sk_test_x'; process.env.STRIPE_WEBHOOK_SECRET = 'whsec_x';
    mockState.constructShouldThrow = true;
    const res = mkRes();
    await webhook(mkRawReq(JSON.stringify({ type: 'checkout.session.completed' }), { 'stripe-signature': 'bad' }), res);
    mockState.constructShouldThrow = false;
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error, 'invalid_signature');
  });
  await t('has bodyParser disabled (raw body required for signature checking)', () => {
    assert.strictEqual(webhook.config.api.bodyParser, false);
  });
  await t('grants a session-keyed entitlement on checkout.session.completed', async () => {
    clearEnv();
    process.env.STRIPE_SECRET_KEY = 'sk_test_x'; process.env.STRIPE_WEBHOOK_SECRET = 'whsec_x';
    await store._reset();
    const evt = JSON.stringify({
      type: 'checkout.session.completed',
      data: { object: { id: 'cs_paid_1', mode: 'payment', metadata: { tier: 'audit' }, customer_details: { email: 'b@u.com' } } },
    });
    const res = mkRes();
    await webhook(mkRawReq(evt, { 'stripe-signature': 'ok' }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(await store.isPaid('sess:cs_paid_1'), true);
  });
  await t('ignores unrelated event types without granting anything', async () => {
    clearEnv();
    process.env.STRIPE_SECRET_KEY = 'sk_test_x'; process.env.STRIPE_WEBHOOK_SECRET = 'whsec_x';
    await store._reset();
    const evt = JSON.stringify({ type: 'invoice.paid', data: { object: { id: 'in_1' } } });
    const res = mkRes();
    await webhook(mkRawReq(evt, { 'stripe-signature': 'ok' }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(await store.isPaid('sess:in_1'), false);
  });

  console.log('\nentitlement route');
  await t('reports not-entitled for an unknown session', async () => {
    await store._reset();
    const res = mkRes();
    await entitlement(mkReq({ method: 'GET', query: { session_id: 'cs_unknown' } }), res);
    assert.strictEqual(res.body.entitled, false);
  });
  await t('reports entitled after the webhook grant', async () => {
    await store._reset();
    await store.setPaid('sess:cs_ok', { product: 'hcf-header-audit', tier: 'audit' });
    const res = mkRes();
    await entitlement(mkReq({ method: 'GET', query: { session_id: 'cs_ok' } }), res);
    assert.strictEqual(res.body.entitled, true);
    assert.strictEqual(res.body.record.product, 'hcf-header-audit');
  });
  await t('requires a session_id', async () => {
    const res = mkRes();
    await entitlement(mkReq({ method: 'GET', query: {} }), res);
    assert.strictEqual(res.statusCode, 400);
  });

  console.log('\nfull audit gate');
  await t('is INERT (501) with no keys and no dev unlock', async () => {
    clearEnv(); await store._reset();
    const res = mkRes();
    await generate(mkReq({ body: { headers: SAMPLE_HEADERS } }), res);
    assert.strictEqual(res.statusCode, 501);
  });
  await t('FAILS CLOSED (402) for an unpaid session when keys are set', async () => {
    clearEnv(); await store._reset();
    process.env.STRIPE_SECRET_KEY = 'sk_test_x';
    mockState.sessions.cs_unpaid = { id: 'cs_unpaid', payment_status: 'unpaid', status: 'open' };
    const res = mkRes();
    await generate(mkReq({ body: { headers: SAMPLE_HEADERS, session_id: 'cs_unpaid' } }), res);
    assert.strictEqual(res.statusCode, 402);
    assert.strictEqual(res.body.report, undefined);
  });
  await t('FAILS CLOSED (402) when no session_id is supplied but keys are set', async () => {
    clearEnv(); await store._reset();
    process.env.STRIPE_SECRET_KEY = 'sk_test_x';
    const res = mkRes();
    await generate(mkReq({ body: { headers: SAMPLE_HEADERS } }), res);
    assert.strictEqual(res.statusCode, 402);
  });
  await t('DELIVERS the audit on a store entitlement written by the webhook', async () => {
    clearEnv(); await store._reset();
    await store.setPaid('sess:cs_paid_2', { product: 'hcf-header-audit', tier: 'audit' });
    const res = mkRes();
    await generate(mkReq({ body: { headers: SAMPLE_HEADERS, session_id: 'cs_paid_2' } }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.report.band, 'ELEVATED');
    assert.ok(res.body.report.findings.length > 0);
    assert.ok(res.body.report.disclaimer.includes('NOT A GUARANTEE'));
  });
  await t('DELIVERS when Stripe itself reports the session paid', async () => {
    clearEnv(); await store._reset();
    process.env.STRIPE_SECRET_KEY = 'sk_test_x';
    mockState.sessions.cs_paid_3 = { id: 'cs_paid_3', payment_status: 'paid', status: 'complete' };
    const res = mkRes();
    await generate(mkReq({ body: { headers: SAMPLE_HEADERS, session_id: 'cs_paid_3' } }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.ok(res.body.report.text.length > 0);
  });
  await t('dev unlock delivers and is labelled as dev, not payment', async () => {
    clearEnv(); await store._reset();
    process.env.HEADER_DEV_UNLOCK = '1';
    const res = mkRes();
    await generate(mkReq({ body: { headers: SAMPLE_HEADERS } }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.dev_unlock, true);
  });
  await t('rejects an entitled request with no headers (400, no report)', async () => {
    clearEnv(); await store._reset();
    process.env.HEADER_DEV_UNLOCK = '1';
    const res = mkRes();
    await generate(mkReq({ body: {} }), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.report, undefined);
  });
  await t('surfaces an unreadable paste as 400 with no report attached', async () => {
    clearEnv(); await store._reset();
    process.env.HEADER_DEV_UNLOCK = '1';
    const res = mkRes();
    await generate(mkReq({ body: { headers: 'just prose, no headers at all' } }), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error, 'NO_HEADERS');
    assert.strictEqual(res.body.report, undefined);
  });
  await t('parses a JSON string body', async () => {
    clearEnv(); await store._reset();
    process.env.HEADER_DEV_UNLOCK = '1';
    const res = mkRes();
    await generate(mkReq({ body: JSON.stringify({ headers: SAMPLE_HEADERS }) }), res);
    assert.strictEqual(res.statusCode, 200);
  });

  console.log('\nfree preview');
  await t('works with NO payment configured at all', async () => {
    clearEnv();
    const res = mkRes();
    await preview(mkReq({ body: { headers: SAMPLE_HEADERS } }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.preview.locked, true);
  });
  await t('never leaks finding details in the free preview', async () => {
    clearEnv();
    const res = mkRes();
    await preview(mkReq({ body: { headers: SAMPLE_HEADERS } }), res);
    const blob = JSON.stringify(res.body);
    assert.strictEqual(blob.includes('display_name_address'), false);
    assert.strictEqual(blob.includes('Reply-To points to'), false);
    assert.ok(res.body.preview.counts.high >= 1);
  });
  await t('requires input', async () => {
    const res = mkRes();
    await preview(mkReq({ body: {} }), res);
    assert.strictEqual(res.statusCode, 400);
  });

  console.log(`\nbuyloop: ${pass} passed, ${fail} failed\n`);
  process.exit(fail === 0 ? 0 : 1);
})();
