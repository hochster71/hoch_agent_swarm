// test/buyloop.test.js
//
// HFF — Getting-Paid Speed Report — buy-loop tests: checkout -> signed webhook
// -> entitlement -> gated delivery. Zero dependencies, no network, no Stripe
// keys. `node test/buyloop.test.js`
//
// These exercise the REAL handlers with a fake req/res. Everything asserted here
// is behaviour the deployed functions will actually have.
'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const store = require('../lib/store');
const checkout = require('../api/create-checkout-session');
const webhook = require('../api/webhook');
const entitlement = require('../api/entitlement');
const preview = require('../api/preview');
const generate = require('../api/generate-report');

let passed = 0;
let failed = 0;
async function t(name, fn) {
  try { await fn(); passed += 1; console.log('  ok   ' + name); }
  catch (e) { failed += 1; console.error('  FAIL ' + name + '\n       ' + e.message); }
}

const SAMPLE = fs.readFileSync(path.join(__dirname, '..', 'engine', 'sample', 'sample_invoices.csv'), 'utf8');

function mkRes() {
  return {
    statusCode: null,
    body: null,
    headers: {},
    setHeader(k, v) { this.headers[k] = v; },
    status(c) { this.statusCode = c; return this; },
    json(o) { this.body = o; return this; },
  };
}
function mkReq(method, body, query) {
  return { method, body: body || {}, query: query || {}, headers: {} };
}
function clearEnv() {
  delete process.env.STRIPE_SECRET_KEY;
  delete process.env.STRIPE_PRICE_REPORT;
  delete process.env.STRIPE_WEBHOOK_SECRET;
  delete process.env.PAYTIMING_DEV_UNLOCK;
}

(async function run() {
  console.log('\n=== inert without keys (FOUNDER GATE NOT CROSSED) ===');

  await t('checkout returns 501 with no STRIPE_SECRET_KEY', async () => {
    clearEnv();
    const res = mkRes();
    await checkout(mkReq('POST', { tier: 'report' }), res);
    assert.strictEqual(res.statusCode, 501);
    assert.strictEqual(res.body.error, 'not_configured');
  });

  await t('checkout returns 501 when the price ID is missing', async () => {
    clearEnv();
    process.env.STRIPE_SECRET_KEY = 'sk_test_placeholder_not_a_real_key';
    const res = mkRes();
    await checkout(mkReq('POST', { tier: 'report' }), res);
    assert.strictEqual(res.statusCode, 501);
    assert.strictEqual(res.body.error, 'price_not_configured');
    clearEnv();
  });

  await t('checkout rejects an unknown tier', async () => {
    clearEnv();
    process.env.STRIPE_SECRET_KEY = 'sk_test_placeholder';
    process.env.STRIPE_PRICE_REPORT = 'price_placeholder';
    const res = mkRes();
    await checkout(mkReq('POST', { tier: 'nope' }), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error, 'invalid_tier');
    clearEnv();
  });

  await t('webhook returns 501 with no keys', async () => {
    clearEnv();
    const res = mkRes();
    await webhook(mkReq('POST'), res);
    assert.strictEqual(res.statusCode, 501);
  });

  await t('generate-report returns 501 when nothing is configured', async () => {
    clearEnv();
    const res = mkRes();
    await generate(mkReq('POST', { csv: SAMPLE }), res);
    assert.strictEqual(res.statusCode, 501);
    assert.strictEqual(res.body.error, 'not_entitled');
  });

  await t('no Stripe key or secret is hardcoded anywhere in the product', async () => {
    const root = path.join(__dirname, '..');
    const suspicious = [];
    const walk = (dir) => {
      for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
        if (e.name === 'node_modules' || e.name === '.git') continue;
        const p = path.join(dir, e.name);
        if (e.isDirectory()) { walk(p); continue; }
        if (!/\.(js|json|html|md)$/.test(e.name)) continue;
        const txt = fs.readFileSync(p, 'utf8');
        if (/sk_live_[A-Za-z0-9]{10,}/.test(txt)) suspicious.push(p + ' (sk_live)');
        if (/whsec_[A-Za-z0-9]{20,}/.test(txt)) suspicious.push(p + ' (whsec)');
        if (/rk_live_[A-Za-z0-9]{10,}/.test(txt)) suspicious.push(p + ' (rk_live)');
      }
    };
    walk(root);
    assert.deepStrictEqual(suspicious, [], 'possible secret material: ' + suspicious.join(', '));
  });

  console.log('\n=== method guards ===');

  await t('checkout rejects GET with 405 and an Allow header', async () => {
    const res = mkRes();
    await checkout(mkReq('GET'), res);
    assert.strictEqual(res.statusCode, 405);
    assert.strictEqual(res.headers.Allow, 'POST');
  });
  await t('webhook rejects GET with 405', async () => {
    const res = mkRes();
    await webhook(mkReq('GET'), res);
    assert.strictEqual(res.statusCode, 405);
  });
  await t('preview rejects GET with 405', async () => {
    const res = mkRes();
    await preview(mkReq('GET'), res);
    assert.strictEqual(res.statusCode, 405);
  });
  await t('generate-report rejects GET with 405', async () => {
    const res = mkRes();
    await generate(mkReq('GET'), res);
    assert.strictEqual(res.statusCode, 405);
  });
  await t('entitlement rejects POST with 405', async () => {
    const res = mkRes();
    await entitlement(mkReq('POST'), res);
    assert.strictEqual(res.statusCode, 405);
  });

  console.log('\n=== webhook signature (FAIL CLOSED) ===');

  await t('webhook with keys set but no valid signature does NOT succeed', async () => {
    clearEnv();
    process.env.STRIPE_SECRET_KEY = 'sk_test_placeholder';
    process.env.STRIPE_WEBHOOK_SECRET = 'whsec_placeholder';
    const res = mkRes();
    const req = mkReq('POST');
    req.on = (ev, cb) => { if (ev === 'end') cb(); return req; };
    await webhook(req, res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error, 'invalid_signature');
    clearEnv();
  });

  await t('webhook exports the bodyParser:false config AFTER the handler (regression)', async () => {
    assert.strictEqual(typeof webhook, 'function');
    assert.deepStrictEqual(webhook.config, { api: { bodyParser: false } });
  });

  console.log('\n=== free preview (ungated, real subset) ===');

  await t('preview works with no keys and returns real top-line figures', async () => {
    clearEnv();
    const res = mkRes();
    await preview(mkReq('POST', { csv: SAMPLE }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.preview, true);
    assert.ok(res.body.timing.billed > 0);
    assert.ok(Array.isArray(res.body.topClients) && res.body.topClients.length >= 1);
    assert.ok(res.body.withheld && /unlocked after purchase/i.test(res.body.withheld));
  });

  await t('preview withholds the paid artifacts (no xlsx/pdf, no full client table)', async () => {
    clearEnv();
    const res = mkRes();
    await preview(mkReq('POST', { csv: SAMPLE }), res);
    assert.strictEqual(res.body.files, undefined);
    assert.ok(res.body.topClients.length <= 3);
  });

  await t('preview maps MISSING_COLUMNS to 400', async () => {
    clearEnv();
    const res = mkRes();
    await preview(mkReq('POST', { csv: 'date,client,amount\n2026-01-01,X,100' }), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error, 'MISSING_COLUMNS');
  });

  await t('preview rejects a missing csv field', async () => {
    clearEnv();
    const res = mkRes();
    await preview(mkReq('POST', {}), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error, 'no_csv');
  });

  console.log('\n=== entitlement + gated delivery ===');

  await t('entitlement reports false for an unknown session', async () => {
    clearEnv();
    await store._reset();
    const res = mkRes();
    await entitlement(mkReq('GET', null, { session_id: 'never_paid' }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.paid, false);
  });

  await t('a signed-webhook-style store grant unlocks the paid report', async () => {
    clearEnv();
    await store._reset();
    await store.setPaid('sess:CS_TEST_1', { product: 'hff-payment-timing', tier: 'report' });

    const eRes = mkRes();
    await entitlement(mkReq('GET', null, { session_id: 'CS_TEST_1' }), eRes);
    assert.strictEqual(eRes.body.paid, true);

    const gRes = mkRes();
    await generate(mkReq('POST', { csv: SAMPLE, session_id: 'CS_TEST_1' }), gRes);
    assert.strictEqual(gRes.statusCode, 200);
    assert.strictEqual(gRes.body.ok, true);
    assert.strictEqual(gRes.body.entitled_via, 'store');
    assert.ok(gRes.body.files.xlsx.base64.length > 100);
    assert.ok(gRes.body.files.pdf.base64.length > 100);
    assert.ok(gRes.body.report.clients.length >= 1);
    // the returned client objects must not leak the internal raw rows array
    assert.strictEqual(gRes.body.report.clients[0].rows, undefined);
  });

  await t('an unpaid session cannot pull the report (fails closed)', async () => {
    clearEnv();
    await store._reset();
    process.env.STRIPE_SECRET_KEY = 'sk_test_placeholder';
    const res = mkRes();
    await generate(mkReq('POST', { csv: SAMPLE, session_id: 'CS_UNPAID' }), res);
    assert.ok(res.statusCode === 402 || res.statusCode === 401,
      'unpaid/unverifiable session must not deliver (got ' + res.statusCode + ')');
    assert.notStrictEqual(res.body.ok, true);
    clearEnv();
  });

  await t('402 when a secret key is set but no session is provided', async () => {
    clearEnv();
    process.env.STRIPE_SECRET_KEY = 'sk_test_placeholder';
    const res = mkRes();
    await generate(mkReq('POST', { csv: SAMPLE }), res);
    assert.strictEqual(res.statusCode, 402);
    clearEnv();
  });

  await t('DEV unlock generates the report without Stripe (local only)', async () => {
    clearEnv();
    process.env.PAYTIMING_DEV_UNLOCK = '1';
    const res = mkRes();
    await generate(mkReq('POST', { csv: SAMPLE }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.dev_unlock, true);
    assert.ok(res.body.files.xlsx.bytes > 0 && res.body.files.pdf.bytes > 0);
    clearEnv();
  });

  await t('generate-report maps a bad CSV to 400 even for an entitled caller', async () => {
    clearEnv();
    process.env.PAYTIMING_DEV_UNLOCK = '1';
    const res = mkRes();
    await generate(mkReq('POST', { csv: 'date,client,amount\n2026-01-01,X,100' }), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error, 'MISSING_COLUMNS');
    clearEnv();
  });

  await t('bad JSON body is rejected with 400', async () => {
    clearEnv();
    process.env.PAYTIMING_DEV_UNLOCK = '1';
    const res = mkRes();
    await generate(mkReq('POST', '{not json'), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error, 'bad_json');
    clearEnv();
  });

  console.log('\n=== store primitives ===');

  await t('store setPaid / isPaid / setUnpaid round-trip', async () => {
    await store._reset();
    assert.strictEqual(await store.isPaid('sess:Z'), false);
    await store.setPaid('sess:Z', { tier: 'report' });
    assert.strictEqual(await store.isPaid('sess:Z'), true);
    await store.setUnpaid('sess:Z');
    assert.strictEqual(await store.isPaid('sess:Z'), false);
  });

  console.log(`\n${passed} passed, ${failed} failed\n`);
  if (failed > 0) process.exit(1);
})();
