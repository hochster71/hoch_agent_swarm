// test/buyloop.test.js
//
// HFF — Vendor Spend Rollup — buy-loop tests: checkout -> signed webhook ->
// entitlement -> gated delivery. Zero dependencies, no network, no Stripe keys.
// `node test/buyloop.test.js`
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

const SAMPLE = fs.readFileSync(path.join(__dirname, '..', 'engine', 'sample', 'sample_expenses.csv'), 'utf8');

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
  delete process.env.VENDORSPEND_DEV_UNLOCK;
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
        // Real Stripe credentials, not the placeholder strings in .env.example.
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

  console.log('\n=== webhook config survives module.exports assignment ===');

  await t('webhook exports config with bodyParser disabled', async () => {
    // Regression guard: assigning module.exports AFTER setting .config would
    // silently discard it, Vercel would pre-parse the body, the raw bytes would
    // be gone, and EVERY signature verification would fail in production.
    assert.ok(webhook.config, 'webhook.config was discarded by the exports assignment');
    assert.strictEqual(webhook.config.api.bodyParser, false);
  });

  console.log('\n=== entitlement store ===');

  await t('an unknown session is not paid', async () => {
    await store._reset();
    assert.strictEqual(await store.isPaid('sess:nope'), false);
  });

  await t('setPaid then isPaid round-trips', async () => {
    await store._reset();
    await store.setPaid('sess:cs_test_1', { product: 'hff-vendor-spend', tier: 'report' });
    assert.strictEqual(await store.isPaid('sess:cs_test_1'), true);
  });

  await t('setUnpaid revokes an entitlement', async () => {
    await store._reset();
    await store.setPaid('sess:cs_test_2', {});
    await store.setUnpaid('sess:cs_test_2');
    assert.strictEqual(await store.isPaid('sess:cs_test_2'), false);
  });

  await t('the store falls back to memory with no KV credentials', async () => {
    delete process.env.KV_REST_API_URL;
    delete process.env.KV_REST_API_TOKEN;
    assert.strictEqual(store.kvConfigured(), false);
  });

  await t('entitlement endpoint reports false for an unknown session', async () => {
    await store._reset();
    const res = mkRes();
    await entitlement(mkReq('GET', null, { session_id: 'cs_unknown' }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.paid, false);
  });

  await t('entitlement endpoint reports true after a grant', async () => {
    await store._reset();
    await store.setPaid('sess:cs_paid_1', {});
    const res = mkRes();
    await entitlement(mkReq('GET', null, { session_id: 'cs_paid_1' }), res);
    assert.strictEqual(res.body.paid, true);
    assert.strictEqual(res.body.source, 'session');
  });

  await t('entitlement endpoint reports false with no session_id at all', async () => {
    const res = mkRes();
    await entitlement(mkReq('GET', null, {}), res);
    assert.strictEqual(res.body.paid, false);
  });

  console.log('\n=== free preview (ungated, real engine) ===');

  await t('preview returns real figures without any payment', async () => {
    clearEnv();
    const res = mkRes();
    await preview(mkReq('POST', { csv: SAMPLE }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.preview, true);
    assert.ok(res.body.spend.net > 0);
    assert.ok(res.body.counts.vendors > 1);
  });

  await t('preview figures match a direct engine run (not fabricated)', async () => {
    const { analyze } = require('../engine');
    const direct = analyze(SAMPLE);
    const res = mkRes();
    await preview(mkReq('POST', { csv: SAMPLE }), res);
    assert.strictEqual(res.body.spend.net, direct.summary.spend.net);
    assert.strictEqual(res.body.counts.vendors, direct.summary.counts.vendors);
    assert.strictEqual(res.body.topVendors[0].label, direct.analysis.vendors[0].label);
  });

  await t('preview withholds the paid surface', async () => {
    const res = mkRes();
    await preview(mkReq('POST', { csv: SAMPLE }), res);
    assert.strictEqual(res.body.files, undefined, 'preview must not ship artifacts');
    assert.strictEqual(res.body.monthly, undefined, 'preview must not ship the monthly series');
    assert.strictEqual(res.body.categories, undefined, 'preview must not ship the category rollup');
    assert.strictEqual(res.body.skipped, undefined, 'preview must not ship flagged-row detail');
    assert.ok(res.body.topVendors.length <= 3, 'preview must cap the vendor list');
    assert.ok(res.body.withheld && res.body.withheld.length > 20);
  });

  await t('preview carries the disclaimer', async () => {
    const res = mkRes();
    await preview(mkReq('POST', { csv: SAMPLE }), res);
    assert.ok(res.body.disclaimer.includes('organizational tooling only'));
  });

  await t('preview maps a missing-column error to 400', async () => {
    const res = mkRes();
    await preview(mkReq('POST', { csv: 'foo,bar\n1,2' }), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error, 'MISSING_COLUMNS');
  });

  await t('preview maps an oversized file to 413', async () => {
    const res = mkRes();
    await preview(mkReq('POST', { csv: 'x'.repeat(9 * 1024 * 1024) }), res);
    assert.strictEqual(res.statusCode, 413);
  });

  await t('preview rejects a missing csv field with 400', async () => {
    const res = mkRes();
    await preview(mkReq('POST', {}), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error, 'no_csv');
  });

  await t('preview parses a stringified JSON body', async () => {
    const res = mkRes();
    await preview(mkReq('POST', JSON.stringify({ csv: SAMPLE })), res);
    assert.strictEqual(res.statusCode, 200);
  });

  await t('preview rejects a malformed JSON body with 400', async () => {
    const res = mkRes();
    await preview(mkReq('POST', '{not json'), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error, 'bad_json');
  });

  console.log('\n=== gated delivery ===');

  await t('paid report is refused without an entitlement (402 once keys exist)', async () => {
    clearEnv();
    await store._reset();
    process.env.STRIPE_SECRET_KEY = 'sk_test_placeholder_not_a_real_key';
    const res = mkRes();
    await generate(mkReq('POST', { csv: SAMPLE }), res);
    assert.strictEqual(res.statusCode, 402);
    assert.strictEqual(res.body.error, 'not_entitled');
    clearEnv();
  });

  await t('a store entitlement unlocks the full report', async () => {
    clearEnv();
    await store._reset();
    await store.setPaid('sess:cs_ok_1', { tier: 'report' });
    const res = mkRes();
    await generate(mkReq('POST', { csv: SAMPLE, session_id: 'cs_ok_1' }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.entitled_via, 'store');
    assert.strictEqual(res.body.dev_unlock, false);
  });

  await t('the unlocked report ships both artifacts as real bytes', async () => {
    await store._reset();
    await store.setPaid('sess:cs_ok_2', {});
    const res = mkRes();
    await generate(mkReq('POST', { csv: SAMPLE, session_id: 'cs_ok_2' }), res);
    const f = res.body.files;
    assert.ok(f.xlsx.bytes > 3000, 'xlsx too small');
    assert.ok(f.pdf.bytes > 1000, 'pdf too small');
    assert.strictEqual(Buffer.from(f.xlsx.base64, 'base64').slice(0, 2).toString('latin1'), 'PK');
    assert.strictEqual(Buffer.from(f.pdf.base64, 'base64').slice(0, 5).toString('latin1'), '%PDF-');
  });

  await t('the unlocked report ships the full paid surface', async () => {
    await store._reset();
    await store.setPaid('sess:cs_ok_3', {});
    const res = mkRes();
    await generate(mkReq('POST', { csv: SAMPLE, session_id: 'cs_ok_3' }), res);
    const r = res.body.report;
    assert.ok(Array.isArray(r.vendors) && r.vendors.length > 3);
    assert.ok(Array.isArray(r.monthly) && r.monthly.length > 1);
    assert.ok(Array.isArray(r.categories) && r.categories.length > 1);
    assert.ok(Array.isArray(r.skipped));
    assert.ok(r.concentration && typeof r.concentration.hhi === 'number');
    assert.ok(r.disclaimer.includes('organizational tooling only'));
  });

  await t('per-payment rows are stripped from the vendor objects in the API response', async () => {
    await store._reset();
    await store.setPaid('sess:cs_ok_4', {});
    const res = mkRes();
    await generate(mkReq('POST', { csv: SAMPLE, session_id: 'cs_ok_4' }), res);
    assert.strictEqual(res.body.report.vendors[0].rows, undefined);
  });

  await t('an entitlement for one session does not unlock another', async () => {
    clearEnv();
    await store._reset();
    await store.setPaid('sess:cs_mine', {});
    process.env.STRIPE_SECRET_KEY = 'sk_test_placeholder_not_a_real_key';
    const res = mkRes();
    await generate(mkReq('POST', { csv: SAMPLE, session_id: 'cs_someone_else' }), res);
    assert.strictEqual(res.statusCode, 402);
    clearEnv();
  });

  await t('dev unlock works locally and is labelled as dev', async () => {
    clearEnv();
    await store._reset();
    process.env.VENDORSPEND_DEV_UNLOCK = '1';
    const res = mkRes();
    await generate(mkReq('POST', { csv: SAMPLE }), res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(res.body.dev_unlock, true);
    assert.strictEqual(res.body.entitled_via, 'dev');
    clearEnv();
  });

  await t('an entitled request with a bad CSV still fails honestly (400, no artifacts)', async () => {
    clearEnv();
    await store._reset();
    process.env.VENDORSPEND_DEV_UNLOCK = '1';
    const res = mkRes();
    await generate(mkReq('POST', { csv: 'foo,bar\n1,2' }), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.files, undefined);
    clearEnv();
  });

  await t('an entitled request with no csv field returns 400', async () => {
    clearEnv();
    process.env.VENDORSPEND_DEV_UNLOCK = '1';
    const res = mkRes();
    await generate(mkReq('POST', {}), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error, 'no_csv');
    clearEnv();
  });

  console.log('\n=== checkout contract ===');

  await t('checkout rejects an unknown tier', async () => {
    clearEnv();
    process.env.STRIPE_SECRET_KEY = 'sk_test_placeholder_not_a_real_key';
    process.env.STRIPE_PRICE_REPORT = 'price_placeholder';
    const res = mkRes();
    await checkout(mkReq('POST', { tier: 'enterprise' }), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error, 'invalid_tier');
    clearEnv();
  });

  await t('checkout defaults to the report tier', async () => {
    clearEnv();
    const res = mkRes();
    await checkout(mkReq('POST', {}), res);
    // No key set, so it stops at 501 rather than invalid_tier — the default resolved.
    assert.strictEqual(res.statusCode, 501);
    assert.strictEqual(res.body.error, 'not_configured');
  });

  await t('checkout rejects a malformed JSON body with 400', async () => {
    clearEnv();
    process.env.STRIPE_SECRET_KEY = 'sk_test_placeholder_not_a_real_key';
    const res = mkRes();
    await checkout(mkReq('POST', '{not json'), res);
    assert.strictEqual(res.statusCode, 400);
    assert.strictEqual(res.body.error, 'bad_json');
    clearEnv();
  });

  console.log('\n=== shipped config is safe ===');

  await t('.env.example contains placeholders only', async () => {
    const env = fs.readFileSync(path.join(__dirname, '..', '.env.example'), 'utf8');
    assert.ok(env.includes('STRIPE_SECRET_KEY'));
    assert.ok(env.includes('STRIPE_WEBHOOK_SECRET'));
    assert.ok(env.includes('REPLACE_ME'));
    assert.ok(!/sk_live_[A-Za-z0-9]{10,}/.test(env), 'live key in .env.example');
    assert.ok(!/whsec_[A-Za-z0-9]{20,}/.test(env), 'real webhook secret in .env.example');
  });

  await t('vercel.json is valid JSON with no-store on API routes', async () => {
    const v = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'vercel.json'), 'utf8'));
    assert.strictEqual(v.version, 2);
    const h = v.headers[0].headers.find((x) => x.key === 'Cache-Control');
    assert.strictEqual(h.value, 'no-store');
  });

  await t('package.json test script runs both suites', async () => {
    const p = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'package.json'), 'utf8'));
    assert.ok(p.scripts.test.includes('engine.test.js'));
    assert.ok(p.scripts.test.includes('buyloop.test.js'));
  });

  await t('the landing page states the price and carries the disclaimer', async () => {
    const html = fs.readFileSync(path.join(__dirname, '..', 'public', 'index.html'), 'utf8');
    assert.ok(html.includes('$9'));
    assert.ok(html.includes('organizational tooling only'));
    assert.ok(html.includes('/api/preview'));
    assert.ok(html.includes('/api/create-checkout-session'));
  });

  await t('the success page gates on session_id and carries the disclaimer', async () => {
    const html = fs.readFileSync(path.join(__dirname, '..', 'public', 'success.html'), 'utf8');
    assert.ok(html.includes('session_id'));
    assert.ok(html.includes('/api/entitlement'));
    assert.ok(html.includes('/api/generate-report'));
    assert.ok(html.includes('organizational tooling only'));
  });

  await t('README declares REAL vs STUB and the founder gate', async () => {
    const md = fs.readFileSync(path.join(__dirname, '..', 'README.md'), 'utf8');
    assert.ok(/REAL/.test(md));
    assert.ok(/STUB|NOT BUILT|not built/i.test(md));
    assert.ok(/founder/i.test(md));
  });

  console.log('\n' + '='.repeat(52));
  console.log(`buyloop tests: ${passed} passed, ${failed} failed`);
  console.log('='.repeat(52) + '\n');
  process.exit(failed === 0 ? 0 : 1);
})();
