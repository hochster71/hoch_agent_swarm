// tests/test_webhook.mjs
//
// Proves the buy-loop bridge for HRF Clarity Briefs, zero external deps:
//   1. Unconfigured (no STRIPE_WEBHOOK_SECRET)        -> 501, nothing written.
//   2. Bad signature                                  -> 400, nothing written.
//   3. Valid signed checkout.session.completed        -> 200, token written in the
//      exact JSON format engine/entitlement.py reads; then a spawned Python check
//      confirms the engine gate ACCEPTS and CONSUMES that token.
//   4. Valid monthly event                            -> remaining:null (unlimited).
//
// Run:  node tests/test_webhook.mjs
//
// The webhook module is CommonJS; we load it via createRequire.

import { createRequire } from 'node:module';
import { EventEmitter } from 'node:events';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PRODUCT_ROOT = path.resolve(__dirname, '..');
const WEBHOOK_SECRET = 'whsec_test_secret_for_offline_verification';

let passed = 0;
let failed = 0;
function ok(cond, label) {
  if (cond) { passed++; console.log('  PASS  ' + label); }
  else { failed++; console.log('  FAIL  ' + label); }
}

// ---- test doubles ---------------------------------------------------------
function mockReq(rawBody, sigHeader) {
  const req = new EventEmitter();
  req.method = 'POST';
  req.headers = {};
  if (sigHeader !== undefined) req.headers['stripe-signature'] = sigHeader;
  // Emit the body on next tick so the handler's listeners are attached first.
  process.nextTick(() => {
    if (rawBody != null) req.emit('data', Buffer.from(rawBody));
    req.emit('end');
  });
  return req;
}

function mockRes() {
  return {
    statusCode: null,
    body: null,
    headers: {},
    setHeader(k, v) { this.headers[k] = v; },
    status(code) { this.statusCode = code; return this; },
    json(obj) { this.body = obj; return this; },
  };
}

function signedHeader(rawBody, secret, timestamp = Math.floor(Date.now() / 1000)) {
  const sig = crypto.createHmac('sha256', secret).update(`${timestamp}.${rawBody}`, 'utf8').digest('hex');
  return `t=${timestamp},v1=${sig}`;
}

function eventBody({ id, tier, mode = 'payment', email = 'buyer@example.com' }) {
  return JSON.stringify({
    id: 'evt_' + id,
    type: 'checkout.session.completed',
    data: {
      object: {
        id,
        mode,
        metadata: { product: 'hrf-clarity-briefs', tier },
        customer_details: { email },
      },
    },
  });
}

async function callHandler(handler, req, res) {
  await handler(req, res);
  return res;
}

// ---- run ------------------------------------------------------------------
const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'hrf-entl-'));
const storeFile = path.join(tmpDir, 'entitlements.json');
process.env.HRF_ENTITLEMENTS_PATH = storeFile;

// Fresh require each time so process.env changes (secret present/absent) apply,
// and the store module re-reads the path from env on every call.
function loadWebhook() {
  delete require.cache[require.resolve('../api/webhook.js')];
  delete require.cache[require.resolve('../lib/entitlements.js')];
  return require('../api/webhook.js');
}

function readStore() {
  try { return JSON.parse(fs.readFileSync(storeFile, 'utf8')); } catch { return {}; }
}

console.log('HRF Clarity Briefs — webhook + entitlement bridge tests\n');

// 1) Unconfigured -> 501
{
  delete process.env.STRIPE_WEBHOOK_SECRET;
  const handler = loadWebhook();
  const raw = eventBody({ id: 'cs_unconfigured', tier: 'brief' });
  const res = await callHandler(handler, mockReq(raw, signedHeader(raw, WEBHOOK_SECRET)), mockRes());
  ok(res.statusCode === 501, 'unconfigured (no secret) returns 501');
  ok(res.body && res.body.error === 'not_configured', 'unconfigured error code is not_configured');
  ok(!fs.existsSync(storeFile), 'unconfigured writes nothing to the store');
}

// From here on, the webhook is "configured".
process.env.STRIPE_WEBHOOK_SECRET = WEBHOOK_SECRET;

// 2) Bad signature -> 400, nothing written
{
  const handler = loadWebhook();
  const raw = eventBody({ id: 'cs_forged', tier: 'brief' });
  const res = await callHandler(handler, mockReq(raw, 't=9999999999,v1=deadbeef'), mockRes());
  ok(res.statusCode === 400, 'bad signature returns 400 (fail-closed)');
  ok(res.body && res.body.error === 'invalid_signature', 'bad signature error is invalid_signature');
  ok(!('cs_forged' in readStore()), 'bad signature grants NO token');
}

// 2b) Missing signature header -> 400
{
  const handler = loadWebhook();
  const raw = eventBody({ id: 'cs_nosig', tier: 'brief' });
  const res = await callHandler(handler, mockReq(raw, undefined), mockRes());
  ok(res.statusCode === 400, 'missing signature header returns 400');
}

// 3) Valid one-off brief -> 200, token written {tier:brief, remaining:1}
const BRIEF_TOKEN = 'cs_test_valid_brief_001';
{
  const handler = loadWebhook();
  const raw = eventBody({ id: BRIEF_TOKEN, tier: 'brief', mode: 'payment' });
  const res = await callHandler(handler, mockReq(raw, signedHeader(raw, WEBHOOK_SECRET)), mockRes());
  ok(res.statusCode === 200, 'valid brief event returns 200');
  const store = readStore();
  ok(BRIEF_TOKEN in store, 'valid brief event grants a token keyed by session id');
  ok(store[BRIEF_TOKEN] && store[BRIEF_TOKEN].tier === 'brief', 'granted record tier=brief');
  ok(store[BRIEF_TOKEN] && store[BRIEF_TOKEN].remaining === 1, 'granted record remaining=1 (one-off credit)');
}

// 4) Valid monthly subscription -> remaining:null (unlimited)
const SUB_TOKEN = 'cs_test_valid_monthly_001';
{
  const handler = loadWebhook();
  const raw = eventBody({ id: SUB_TOKEN, tier: 'monthly', mode: 'subscription' });
  const res = await callHandler(handler, mockReq(raw, signedHeader(raw, WEBHOOK_SECRET)), mockRes());
  ok(res.statusCode === 200, 'valid monthly event returns 200');
  const store = readStore();
  ok(store[SUB_TOKEN] && store[SUB_TOKEN].remaining === null, 'monthly record remaining=null (unlimited)');
}

// 5) Cross-language proof: the Python engine gate ACCEPTS + CONSUMES the token.
{
  const py = `
import json, sys
sys.path.insert(0, ${JSON.stringify(PRODUCT_ROOT)})
from engine.entitlement import EntitlementStore, require_entitlement, EntitlementError
store = EntitlementStore(${JSON.stringify(storeFile)})

# one-off brief token: accepted, then consumed to 0, then denied.
assert store.is_entitled(${JSON.stringify(BRIEF_TOKEN)}), "engine should accept the granted brief token"
require_entitlement(${JSON.stringify(BRIEF_TOKEN)}, store=store, consume=True)
assert not store.is_entitled(${JSON.stringify(BRIEF_TOKEN)}), "brief token should be spent after one use"

# subscription token: accepted and NOT consumed (unlimited).
assert store.is_entitled(${JSON.stringify(SUB_TOKEN)}), "engine should accept the monthly token"
require_entitlement(${JSON.stringify(SUB_TOKEN)}, store=store, consume=True)
assert store.is_entitled(${JSON.stringify(SUB_TOKEN)}), "monthly token stays entitled (unlimited)"

# a token that was never granted is denied.
try:
    require_entitlement("cs_never_granted", store=store, consume=True)
    print("FAIL: ungranted token was accepted"); sys.exit(3)
except EntitlementError:
    pass
print("PYOK")
`;
  const r = spawnSync('python3', ['-c', py], { encoding: 'utf8' });
  const good = r.status === 0 && /PYOK/.test(r.stdout || '');
  ok(good, 'Python engine gate accepts+consumes the webhook-granted token');
  if (!good) console.log('    python stdout:', r.stdout, '\n    python stderr:', r.stderr);
}

// cleanup
try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch {}

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed === 0 ? 0 : 1);
