// engine/entitlements.js
//
// HMF Cue Library — entitlement store (mirrors the checkout/entitlement pattern).
//
// In production, a Stripe webhook (checkout.session.completed / an active
// subscription) is the ONLY thing that writes an entitlement here. This module
// deliberately does NOT create entitlements from user input — a caller must
// present proof (a webhook-verified grant). This mirrors the checkout shape:
// create-checkout-session.js starts a paid session; the webhook later grants.
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
// (e.g. Stripe customer id). A subscription grants access to the whole library,
// so `packs: "*"` means all packs; or an explicit list for one-off pack sales.
function grantEntitlement(subject, opts, storePath) {
  if (!subject) throw new Error('grantEntitlement: subject required');
  const store = readStore(storePath);
  store[subject] = {
    subject,
    packs: (opts && opts.packs) || '*',
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

// THE GATE. Returns true only if `subject` has an active entitlement that
// covers `packId`. Everything about delivery hangs off this returning true.
function isEntitled(subject, packId, storePath) {
  if (!subject || !packId) return false;
  const store = readStore(storePath);
  const ent = store[subject];
  if (!ent || ent.active !== true) return false;
  if (ent.packs === '*') return true;
  return Array.isArray(ent.packs) && ent.packs.includes(packId);
}

module.exports = { grantEntitlement, revokeEntitlement, isEntitled, readStore, writeStore, DEFAULT_STORE };
