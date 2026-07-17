// test/test_webhook.js
//
// Proves the PURCHASE -> ACCESS write path at the code level:
//   1) a VALID signed `checkout.session.completed` grants the (pack-scoped)
//      entitlement, so isEntitled() passes and gated delivery succeeds;
//   2) a BAD signature is rejected (400) and grants NOTHING (fail-closed);
//   3) an un-entitled buyer is still DENIED delivery;
//   4) an unconfigured webhook fails safe (501).
//
// No Stripe account, keys, or network. The `stripe` package is mocked via
// Module._load so the test runs with zero install. Pure Node + assert.
// Run: node test/test_webhook.js

'use strict';

const os = require('os');
const path = require('path');
const fs = require('fs');
const assert = require('assert');
const Module = require('module');
const { Readable } = require('stream');

const GOOD_SIG = 'test_good_signature';
const fakeStripeFactory = function () {
  return {
    webhooks: {
      constructEvent(rawBody, signature) {
        if (signature !== GOOD_SIG) {
          const e = new Error('No signatures found matching the expected signature for payload.');
          e.type = 'StripeSignatureVerificationError';
          throw e;
        }
        return JSON.parse(rawBody.toString('utf8'));
      },
    },
  };
};
const origLoad = Module._load;
Module._load = function (request) {
  if (request === 'stripe') return fakeStripeFactory;
  return origLoad.apply(this, arguments);
};

const tmpStore = path.join(os.tmpdir(), 'hmf_pod_wh_ent_' + Date.now() + '.json');
process.env.STINGS_ENTITLEMENTS_PATH = tmpStore;
process.env.STRIPE_SECRET_KEY = 'sk_test_dummy';
process.env.STRIPE_WEBHOOK_SECRET = 'whsec_test_dummy';

const handler = require('../api/webhook');
const { isEntitled } = require('../engine/entitlements');
const { loadCatalog, getPack } = require('../engine/catalog');
const { assemblePack, DeliveryDenied } = require('../engine/packager');

const pack = getPack('cold-open', loadCatalog());

function makeReq(bodyObj, signature) {
  const raw = Buffer.from(JSON.stringify(bodyObj), 'utf8');
  const req = Readable.from([raw]);
  req.method = 'POST';
  req.headers = { 'stripe-signature': signature };
  return req;
}
function makeRes() {
  return {
    statusCode: null, body: null, headers: {},
    setHeader(k, v) { this.headers[k] = v; },
    status(c) { this.statusCode = c; return this; },
    json(o) { this.body = o; return this; },
    send(b) { this.body = b; return this; },
  };
}
function checkoutEvent({ email, subject, pack: packId }) {
  return {
    id: 'evt_test_1',
    type: 'checkout.session.completed',
    data: { object: {
      id: 'cs_test_123', mode: 'payment', customer: 'cus_test_ABC',
      customer_details: { email: email || null },
      metadata: { product: 'hmf-podcast-stings', tier: 'pack', pack: packId || '', subject: subject || '' },
    } },
  };
}

let pass = 0, fail = 0;
async function ok(name, fn) {
  try { await fn(); console.log('  PASS  ' + name); pass++; }
  catch (e) { console.log('  FAIL  ' + name + '  -> ' + e.message); fail++; }
}

(async () => {
  console.log('HMF Podcast Sting Pack — Stripe webhook -> entitlement grant tests\n');

  await ok('valid checkout.session.completed grants (pack-scoped) entitlement', async () => {
    const req = makeReq(checkoutEvent({ email: 'Buyer@HMF.test', pack: 'cold-open' }), GOOD_SIG);
    const res = makeRes();
    await handler(req, res);
    assert.strictEqual(res.statusCode, 200, 'expected 200, got ' + res.statusCode);
    assert(res.body && res.body.received === true, 'expected { received: true }');
    assert.strictEqual(isEntitled('buyer@hmf.test', 'cold-open', tmpStore), true, 'buyer should be entitled after grant');
    const zip = assemblePack(pack, { subject: 'buyer@hmf.test', storePath: tmpStore, requireAudio: false });
    assert(Buffer.isBuffer(zip) && zip.length > 0, 'entitled buyer should receive a zip');
  });

  await ok('per-pack grant does NOT unlock a different pack', async () => {
    assert.strictEqual(isEntitled('buyer@hmf.test', 'quiet-desk', tmpStore), false, 'other pack must remain locked');
  });

  await ok('bad signature is rejected (400) and grants nothing', async () => {
    const req = makeReq(checkoutEvent({ email: 'attacker@evil.test', pack: 'cold-open' }), 'forged_sig');
    const res = makeRes();
    await handler(req, res);
    assert.strictEqual(res.statusCode, 400, 'expected 400 on bad signature, got ' + res.statusCode);
    assert(res.body && res.body.error === 'invalid_signature', 'expected invalid_signature error');
    assert.strictEqual(isEntitled('attacker@evil.test', 'cold-open', tmpStore), false, 'forged event must NOT grant');
  });

  await ok('un-entitled buyer is denied delivery', async () => {
    let threw = null;
    try { assemblePack(pack, { subject: 'stranger@nowhere.test', storePath: tmpStore, requireAudio: false }); }
    catch (e) { threw = e; }
    assert(threw instanceof DeliveryDenied, 'expected DeliveryDenied');
    assert.strictEqual(threw.code, 'not_entitled');
  });

  await ok('unconfigured webhook returns 501 (fail-safe)', async () => {
    const savedKey = process.env.STRIPE_SECRET_KEY;
    const savedSecret = process.env.STRIPE_WEBHOOK_SECRET;
    delete process.env.STRIPE_SECRET_KEY;
    delete process.env.STRIPE_WEBHOOK_SECRET;
    try {
      const req = makeReq(checkoutEvent({ email: 'x@y.test', pack: 'cold-open' }), GOOD_SIG);
      const res = makeRes();
      await handler(req, res);
      assert.strictEqual(res.statusCode, 501, 'expected 501 when unconfigured, got ' + res.statusCode);
    } finally {
      process.env.STRIPE_SECRET_KEY = savedKey;
      process.env.STRIPE_WEBHOOK_SECRET = savedSecret;
    }
  });

  try { fs.unlinkSync(tmpStore); } catch (e) {}
  Module._load = origLoad;

  console.log('\n' + pass + ' passed, ' + fail + ' failed');
  process.exit(fail === 0 ? 0 : 1);
})();
