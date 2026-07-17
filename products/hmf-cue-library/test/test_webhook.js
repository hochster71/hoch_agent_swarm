// test/test_webhook.js
//
// Proves the PURCHASE -> ACCESS write path end to end at the code level:
//   1) a VALID signed `checkout.session.completed` grants the entitlement, so
//      isEntitled() then passes and gated delivery (assemblePack) succeeds;
//   2) a BAD signature is rejected (400) and grants NOTHING (fail-closed);
//   3) an un-entitled buyer is still DENIED delivery.
//
// No Stripe account, keys, or network are used. The `stripe` package is mocked
// via Module._load so the test runs with zero install. Pure Node + assert.
// Run: node test/test_webhook.js

'use strict';

const os = require('os');
const path = require('path');
const fs = require('fs');
const assert = require('assert');
const Module = require('module');
const { Readable } = require('stream');

// ---- Mock the `stripe` package BEFORE api/webhook.js lazily requires it -----
// The fake verifies our test signature and returns the parsed body as the event.
const GOOD_SIG = 'test_good_signature';
const fakeStripeFactory = function () {
  return {
    webhooks: {
      constructEvent(rawBody, signature /*, secret */) {
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
Module._load = function (request, parent, isMain) {
  if (request === 'stripe') return fakeStripeFactory;
  return origLoad.apply(this, arguments);
};

// ---- Isolate the entitlement store to a temp file --------------------------
const tmpStore = path.join(os.tmpdir(), 'hmf_wh_ent_' + Date.now() + '.json');
process.env.HMF_ENTITLEMENTS_PATH = tmpStore;
process.env.STRIPE_SECRET_KEY = 'sk_test_dummy';
process.env.STRIPE_WEBHOOK_SECRET = 'whsec_test_dummy';

const handler = require('../api/webhook');
const { isEntitled } = require('../engine/entitlements');
const { loadCatalog, getPack } = require('../engine/catalog');
const { assemblePack, DeliveryDenied } = require('../engine/packager');

const pack = getPack('midnight-drive', loadCatalog());

// ---- Tiny fake req/res -----------------------------------------------------
function makeReq(bodyObj, signature) {
  const raw = Buffer.from(JSON.stringify(bodyObj), 'utf8');
  const req = Readable.from([raw]); // real stream => readRawBody works unchanged
  req.method = 'POST';
  req.headers = { 'stripe-signature': signature };
  return req;
}
function makeRes() {
  return {
    statusCode: null,
    body: null,
    headers: {},
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
    data: {
      object: {
        id: 'cs_test_123',
        mode: 'subscription',
        customer: 'cus_test_ABC',
        customer_details: { email: email || null },
        metadata: { product: 'hmf-cue-library', tier: 'monthly', pack: packId || '', subject: subject || '' },
      },
    },
  };
}

let pass = 0, fail = 0;
async function ok(name, fn) {
  try { await fn(); console.log('  PASS  ' + name); pass++; }
  catch (e) { console.log('  FAIL  ' + name + '  -> ' + e.message); fail++; }
}

(async () => {
  console.log('HMF Cue Library — Stripe webhook -> entitlement grant tests\n');

  // --- 1. Valid signed checkout grants entitlement; delivery then allowed ---
  await ok('valid checkout.session.completed grants entitlement (pack-scoped)', async () => {
    const req = makeReq(checkoutEvent({ email: 'Buyer@HMF.test', pack: 'midnight-drive' }), GOOD_SIG);
    const res = makeRes();
    await handler(req, res);
    assert.strictEqual(res.statusCode, 200, 'expected 200, got ' + res.statusCode);
    assert(res.body && res.body.received === true, 'expected { received: true }');

    // subject resolves to lowercased email; entitlement now covers the pack.
    assert.strictEqual(isEntitled('buyer@hmf.test', 'midnight-drive', tmpStore), true, 'buyer should be entitled after grant');
    // and gated delivery succeeds (placeholder mode — no audio yet, but gate passes)
    const zip = assemblePack(pack, { subject: 'buyer@hmf.test', storePath: tmpStore, requireAudio: false });
    assert(Buffer.isBuffer(zip) && zip.length > 0, 'entitled buyer should receive a zip');
  });

  // --- 1b. Subscription with no pack => full-library ("*") access ---
  await ok('checkout with no pack grants full-library access ("*")', async () => {
    const req = makeReq(checkoutEvent({ email: 'sub@hmf.test', pack: '' }), GOOD_SIG);
    const res = makeRes();
    await handler(req, res);
    assert.strictEqual(res.statusCode, 200, 'expected 200');
    assert.strictEqual(isEntitled('sub@hmf.test', 'midnight-drive', tmpStore), true, 'wildcard should cover any pack');
    assert.strictEqual(isEntitled('sub@hmf.test', 'sunrise-standup', tmpStore), true, 'wildcard should cover other packs too');
  });

  // --- 2. Bad signature rejected (400) and grants NOTHING ---
  await ok('bad signature is rejected (400) and grants nothing', async () => {
    const req = makeReq(checkoutEvent({ email: 'attacker@evil.test', pack: 'midnight-drive' }), 'forged_sig');
    const res = makeRes();
    await handler(req, res);
    assert.strictEqual(res.statusCode, 400, 'expected 400 on bad signature, got ' + res.statusCode);
    assert(res.body && res.body.error === 'invalid_signature', 'expected invalid_signature error');
    // nothing was written for the forged buyer
    assert.strictEqual(isEntitled('attacker@evil.test', 'midnight-drive', tmpStore), false, 'forged event must NOT grant');
  });

  // --- 3. Un-entitled buyer is still DENIED delivery (fail-closed) ---
  await ok('un-entitled buyer is denied delivery', async () => {
    let threw = null;
    try {
      assemblePack(pack, { subject: 'stranger@nowhere.test', storePath: tmpStore, requireAudio: false });
    } catch (e) { threw = e; }
    assert(threw instanceof DeliveryDenied, 'expected DeliveryDenied');
    assert.strictEqual(threw.code, 'not_entitled', 'expected not_entitled, got ' + (threw && threw.code));
  });

  // --- 4. Unconfigured webhook fails safe (501), no keys => inert ---
  await ok('unconfigured webhook returns 501 (fail-safe)', async () => {
    const savedKey = process.env.STRIPE_SECRET_KEY;
    const savedSecret = process.env.STRIPE_WEBHOOK_SECRET;
    delete process.env.STRIPE_SECRET_KEY;
    delete process.env.STRIPE_WEBHOOK_SECRET;
    try {
      const req = makeReq(checkoutEvent({ email: 'x@y.test', pack: 'midnight-drive' }), GOOD_SIG);
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
