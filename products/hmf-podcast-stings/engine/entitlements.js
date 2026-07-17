// engine/entitlements.js
//
// HMF — Podcast Sting Pack — entitlement store (mirrors the proven cue-library
// checkout/entitlement pattern).
//
// In production, a Stripe webhook (checkout.session.completed) is the ONLY thing
// that writes an entitlement here. This module does NOT create entitlements from
// user input — a caller must present proof (a webhook-verified grant).
//
// Storage is a simple JSON file so the pattern is real and testable without a
// database. Swap `store` for your real datastore in production.

'use strict';

const fs = require('fs');
const path = require('path');

const DEFAULT_STORE = path.join(__dirname, '..', '.data', 'entitlements.json');

function readStore(storePath) {
  const p = storePath || DEFAULT_STORE;
  try {
    return JSON.parse(fs.readFileSync(p, 'utf8'));
  } catch (e) {
    return {}; // fail-closed: no file => nobody is entitled
  }
}

function writeStore(obj, storePath) {
  const p = storePath || DEFAULT_STORE;
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, JSON.stringify(obj, null, 2));
}

// Called by the (webhook) grant path only. `subject` is a stable buyer id
// (e.g. email or Stripe customer id). This is a ONE-TIME per-pack product, so a
// purchase grants an explicit list of pack ids. (A "*" wildcard is still honored
// for a hypothetical bundle.)
function grantEntitlement(subject, opts, storePath) {
  if (!subject) throw new Error('grantEntitlement: subject required');
  const store = readStore(storePath);
  const incoming = (opts && opts.packs) || [];
  const existing = store[subject];
  let packs = incoming;
  // Accumulate packs across multiple one-time purchases by the same buyer.
  if (existing && Array.isArray(existing.packs) && Array.isArray(incoming)) {
    packs = Array.from(new Set(existing.packs.concat(incoming)));
  }
  store[subject] = {
    subject,
    packs,
    active: true,
    granted_utc: new Date().toISOString(),
    source: (opts && opts.source) || 'stripe_webhook',
  };
  writeStore(store, storePath);
  return store[subject];
}

function revokeEntitlement(subject, storePath) {
  const store = readStore(storePath);
  if (store[subject]) {
    store[subject].active = false;
    store[subject].revoked_utc = new Date().toISOString();
    writeStore(store, storePath);
  }
}

// THE GATE. Returns true only if `subject` has an active entitlement that covers
// `packId`.
function isEntitled(subject, packId, storePath) {
  if (!subject || !packId) return false;
  const store = readStore(storePath);
  const ent = store[subject];
  if (!ent || ent.active !== true) return false;
  if (ent.packs === '*') return true;
  return Array.isArray(ent.packs) && ent.packs.includes(packId);
}

module.exports = { grantEntitlement, revokeEntitlement, isEntitled, readStore, writeStore, DEFAULT_STORE };
