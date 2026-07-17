// lib/store.js
//
// Hoch Storybook Factory (HSF) — entitlement key/value store (REAL).
//
// This is the module `api/webhook.js` imports:
//     const { setPaid, put }     = require('../lib/store');   // webhook.js L107
//     const { setUnpaid, get }   = require('../lib/store');   // webhook.js L122, L131
// Its absence made the webhook throw MODULE_NOT_FOUND on the first paid event.
// This implementation matches that exact interface, plus a small `isPaid()`
// helper used by `api/entitlement.js`.
//
// BACKENDS:
//   * @vercel/kv  — used ONLY when KV_REST_API_URL + KV_REST_API_TOKEN are set
//     in the environment (i.e. real Vercel KV provisioned). The require is lazy
//     and guarded, so the module never crashes if the package isn't installed.
//   * in-memory Map — automatic fallback with NO credentials. This is what lets
//     the code run locally and in tests without any KV / Stripe secrets.
//
// KEY CONVENTIONS (as implied by webhook.js):
//   story:<storyId>     -> onestory export unlock  (keyed by client_reference_id)
//   email:<addr>        -> creators subscription unlock (all their stories)
//   cust:<customerId>   -> { email } map, so a cancel/lapse can revoke by email
//
// Record shape written by setPaid: { paid: true, updatedAt, ...meta }.

'use strict';

let _kv = null;      // cached @vercel/kv client (or false once we know it's absent)
let _mem = null;     // in-memory Map fallback

function kvConfigured() {
  return !!(process.env.KV_REST_API_URL && process.env.KV_REST_API_TOKEN);
}

// Resolve the active backend. Returns { type:'kv', kv } or { type:'mem', mem }.
function backend() {
  if (kvConfigured() && _kv !== false) {
    if (!_kv) {
      try {
        // Lazy + guarded: absent package must NOT crash the store.
        // eslint-disable-next-line global-require
        _kv = require('@vercel/kv').kv;
      } catch (e) {
        console.warn('[store] @vercel/kv not installed; using in-memory fallback.');
        _kv = false;
      }
    }
    if (_kv) return { type: 'kv', kv: _kv };
  }
  if (!_mem) _mem = new Map();
  return { type: 'mem', mem: _mem };
}

// get(key) -> stored value (object) or null.
async function get(key) {
  const b = backend();
  if (b.type === 'kv') {
    const v = await b.kv.get(key);
    return v == null ? null : v;
  }
  return b.mem.has(key) ? b.mem.get(key) : null;
}

// put(key, value) -> store a raw value.
async function put(key, value) {
  const b = backend();
  if (b.type === 'kv') {
    await b.kv.set(key, value);
    return;
  }
  b.mem.set(key, value);
}

// setPaid(key, meta) -> mark an entitlement paid. Returns the written record.
async function setPaid(key, meta) {
  const record = Object.assign(
    { paid: true, updatedAt: new Date().toISOString() },
    meta || {}
  );
  await put(key, record);
  return record;
}

// setUnpaid(key) -> revoke an entitlement (kept as a record for auditability).
async function setUnpaid(key) {
  const existing = (await get(key)) || {};
  const record = Object.assign({}, existing, {
    paid: false,
    updatedAt: new Date().toISOString(),
  });
  await put(key, record);
  return record;
}

// isPaid(key) -> boolean. Used by api/entitlement.js and gated stubs.
async function isPaid(key) {
  const record = await get(key);
  return !!(record && record.paid === true);
}

// Test-only helper: clear the in-memory backend between test cases.
async function _reset() {
  if (_mem) _mem.clear();
}

module.exports = { get, put, setPaid, setUnpaid, isPaid, kvConfigured, _reset };
