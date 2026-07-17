#!/usr/bin/env node
// =============================================================================
// hsf/deploy/preflight_check.mjs
// Story Studio GO-LIVE preflight — PURE LOCAL VALIDATION.
//
// WHAT IT DOES: after you have set your env vars (in a local .env or exported
// in the shell), this verifies they are present, non-placeholder, and
// well-formed BEFORE you deploy or attempt a real purchase.
//
// WHAT IT DOES NOT DO: it makes NO network calls. It never talks to Stripe,
// Vercel, or KV. It never charges anything and never verifies a key is "live"
// against Stripe's servers — that is impossible without a network call and is
// intentionally out of scope. A PASS here means "the values are shaped
// correctly and nothing is an obvious placeholder", NOT "Stripe accepted them".
//
// USAGE:
//   # Option A — load a local .env first (Node 20.6+):
//   node --env-file=.env preflight_check.mjs
//   # Option B — if your env is already exported in the shell:
//   node preflight_check.mjs
//
// EXIT CODES: 0 = all required checks passed. 1 = one or more failed (details
// printed). Dependency-free: uses only Node built-ins.
// =============================================================================

'use strict';

// Values equal to any of these (case-insensitive) are treated as "not set".
const PLACEHOLDER_TOKENS = [
  'FILL_ME',
  'REPLACE_ME',
  'CHANGE_ME',
  'YOUR_',
  'xxxx',
];

function isPlaceholder(value) {
  if (value === undefined || value === null) return true;
  const v = String(value).trim();
  if (v === '') return true;
  const upper = v.toUpperCase();
  return PLACEHOLDER_TOKENS.some((tok) => upper.includes(tok.toUpperCase()));
}

const failures = [];
const warnings = [];
const passes = [];

// check(name, opts): validates one env var.
//   required: fail if missing/placeholder (default true).
//   prefix:   value must start with this string (e.g. 'sk_').
//   regex:    value must match this pattern.
//   hint:     where to get it, printed on failure.
function check(name, opts = {}) {
  const { required = true, prefix, regex, hint = '' } = opts;
  const raw = process.env[name];

  if (isPlaceholder(raw)) {
    if (required) {
      failures.push(`${name} is missing or still a placeholder.${hint ? ' -> ' + hint : ''}`);
    } else {
      warnings.push(`${name} is not set (optional).${hint ? ' -> ' + hint : ''}`);
    }
    return;
  }

  const val = String(raw).trim();

  if (prefix && !val.startsWith(prefix)) {
    failures.push(`${name} does not start with "${prefix}" (got "${val.slice(0, 8)}...").${hint ? ' -> ' + hint : ''}`);
    return;
  }
  if (regex && !regex.test(val)) {
    failures.push(`${name} is set but malformed (expected ${regex}).${hint ? ' -> ' + hint : ''}`);
    return;
  }
  passes.push(`${name} present and well-formed.`);
}

console.log('HSF Story Studio — GO-LIVE preflight (local, no network)\n');

// --- REQUIRED: Stripe secret key -------------------------------------------
// Accept sk_live_ (real earning) or sk_test_ (rehearsal). Warn on test.
check('STRIPE_SECRET_KEY', {
  prefix: 'sk_',
  regex: /^sk_(live|test)_[A-Za-z0-9]+$/,
  hint: 'Stripe Dashboard > Developers > API keys > Secret key',
});
if (!isPlaceholder(process.env.STRIPE_SECRET_KEY)) {
  const sk = String(process.env.STRIPE_SECRET_KEY).trim();
  if (sk.startsWith('sk_test_')) {
    warnings.push('STRIPE_SECRET_KEY is a TEST key (sk_test_). Real earning needs a LIVE key (sk_live_).');
  }
}

// --- REQUIRED: webhook signing secret --------------------------------------
check('STRIPE_WEBHOOK_SECRET', {
  prefix: 'whsec_',
  regex: /^whsec_[A-Za-z0-9]+$/,
  hint: 'Stripe Dashboard > Developers > Webhooks > your endpoint > Signing secret (set AFTER deploy)',
});

// --- REQUIRED: price IDs ----------------------------------------------------
check('STRIPE_PRICE_ONESTORY', {
  prefix: 'price_',
  regex: /^price_[A-Za-z0-9]+$/,
  hint: 'Stripe Dashboard > Product catalog > $19 one-time product > price API ID',
});
check('STRIPE_PRICE_CREATORS', {
  prefix: 'price_',
  regex: /^price_[A-Za-z0-9]+$/,
  hint: 'Stripe Dashboard > Product catalog > $12/mo product > price API ID',
});

// Cross-check: onestory and creators must be DIFFERENT price IDs.
{
  const a = process.env.STRIPE_PRICE_ONESTORY;
  const b = process.env.STRIPE_PRICE_CREATORS;
  if (!isPlaceholder(a) && !isPlaceholder(b) && String(a).trim() === String(b).trim()) {
    failures.push('STRIPE_PRICE_ONESTORY and STRIPE_PRICE_CREATORS are identical — they must be two different prices.');
  }
}

// Cross-check: secret key mode vs. price ID naming is NOT verifiable offline,
// so we only note it. (Live price IDs are not visually distinguishable from
// test ones — only Stripe can confirm. This is why runbook step (f) does a
// real $19 test purchase.)

// --- REQUIRED: base URL -----------------------------------------------------
check('BASE_URL', {
  regex: /^https?:\/\/.+/,
  hint: 'Your deployed domain, e.g. https://storybook.hoch.app or the *.vercel.app URL',
});
if (!isPlaceholder(process.env.BASE_URL)) {
  const b = String(process.env.BASE_URL).trim();
  if (b.startsWith('http://localhost') || b.startsWith('http://127.')) {
    warnings.push('BASE_URL points at localhost — fine for local rehearsal, WRONG for production redirects.');
  }
  if (b.startsWith('http://') && !b.startsWith('http://localhost') && !b.startsWith('http://127.')) {
    warnings.push('BASE_URL uses http:// (not https://). Stripe redirects and cookies expect https in production.');
  }
}

// --- REQUIRED for durable entitlements: Vercel KV ---------------------------
// If EITHER is missing, lib/store.js silently uses an in-memory Map that is
// wiped on cold start — a paid entitlement can vanish. Treat as required for
// go-live; downgrade to warning only if you have accepted that risk.
check('KV_REST_API_URL', {
  regex: /^https?:\/\/.+/,
  hint: 'Vercel Dashboard > Storage > your KV store > .env.local tab (auto-injected when connected)',
});
check('KV_REST_API_TOKEN', {
  hint: 'Vercel Dashboard > Storage > your KV store > .env.local tab (auto-injected when connected)',
});

// --- OPTIONAL: AUTH_SECRET (reserved; not yet enforced) ---------------------
// Not read by any live code path yet (magic-link is a 501 stub). Recommended
// to set now so it is ready, but its absence does NOT block the $19 buy loop.
check('AUTH_SECRET', {
  required: false,
  hint: 'Generate with: openssl rand -base64 32',
});

// --- Report -----------------------------------------------------------------
console.log(`PASS (${passes.length}):`);
for (const p of passes) console.log('  [ok] ' + p);

if (warnings.length) {
  console.log(`\nWARNINGS (${warnings.length}) — non-blocking, but read them:`);
  for (const w of warnings) console.log('  [warn] ' + w);
}

if (failures.length) {
  console.log(`\nFAILURES (${failures.length}) — fix these before deploying / purchasing:`);
  for (const f of failures) console.log('  [FAIL] ' + f);
  console.log('\nPreflight FAILED. See hsf/deploy/.env.template for names and sources.');
  process.exit(1);
}

console.log('\nPreflight PASSED (local checks only).');
console.log('Reminder: this did NOT contact Stripe. Prove the live path with the');
console.log('ONE real $19 test purchase + refund in docs/founder/story_studio_go_live_runbook.md.');
process.exit(0);
