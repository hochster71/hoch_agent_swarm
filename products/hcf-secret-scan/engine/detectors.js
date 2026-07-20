// engine/detectors.js
//
// OFFLINE, deterministic credential-pattern detectors. String matching only:
// no network, no vendor API calls, no validation of whether a match is a real,
// active credential. Every explanation carries a benign alternative — that is
// the product's honesty guardrail, enforced downstream by the report linter.
'use strict';

const { shannonEntropy } = require('./entropy');

// Values that look like templates/examples, not real credentials.
const PLACEHOLDER_RE = /replace|example|your[_-]?|change[_-]?me|xxxx|<[^>]{0,60}>|\$\{[^}]{0,60}\}|%[A-Z0-9_]+%|\.\.\.|dummy|sample|placeholder|todo|redacted|fixme|insert[_-]?/i;
const ENV_REF_RE = /^\$[A-Za-z_][A-Za-z0-9_]*$/;

function isPlaceholder(value) {
  return PLACEHOLDER_RE.test(value) || ENV_REF_RE.test(value);
}

// Vendor key formats. "Matches the documented format of X" is a string claim,
// not a validity claim — the benign text says so every time.
const VENDOR = [
  {
    id: 'aws_access_key_id', severity: 'high', label: 'AWS Access Key ID format',
    re: /\b(?:AKIA|ASIA)[0-9A-Z]{16}\b/g,
    explain: 'Matches the documented format of an AWS access key identifier (AKIA/ASIA prefix + 16 characters).',
    benign: 'A format match alone does not show the key is active — it may be revoked, expired, randomly generated, or synthetic demo data.',
  },
  {
    id: 'github_token', severity: 'high', label: 'GitHub token format',
    re: /\bgh[pousr]_[A-Za-z0-9]{36}\b/g,
    explain: 'Matches the documented format of a GitHub personal access / OAuth / app token (gh?_ prefix + 36 characters).',
    benign: 'The token may already be revoked or expired; the format does not reveal its scopes or whether it works.',
  },
  {
    id: 'stripe_webhook_secret', severity: 'high', label: 'Stripe webhook signing secret format',
    re: /\bwhsec_[A-Za-z0-9]{16,}\b/g,
    explain: 'Matches the format of a Stripe webhook signing secret (whsec_ prefix).',
    benign: 'Signing secrets are per-endpoint and rotate without breaking anything else; this one may already be rolled or belong to a test endpoint.',
  },
  {
    id: 'stripe_live_key', severity: 'high', label: 'Stripe live secret key format',
    re: /\b(?:sk|rk)_live_[A-Za-z0-9]{16,}\b/g,
    explain: 'Matches the format of a Stripe LIVE-mode secret or restricted key (sk_live_/rk_live_).',
    benign: 'The key may be revoked, or a restricted key with narrow permissions; the format does not show what it can do.',
  },
  {
    id: 'stripe_test_key', severity: 'low', label: 'Stripe test-mode key format',
    re: /\b(?:sk|rk)_test_[A-Za-z0-9]{16,}\b/g,
    explain: 'Matches the format of a Stripe TEST-mode key (sk_test_/rk_test_). Test-mode keys cannot move real money.',
    benign: 'Test keys are commonly shared in fixtures and docs; many projects treat them as non-sensitive.',
  },
  {
    id: 'slack_token', severity: 'high', label: 'Slack token format',
    re: /\bxox[baprs]-[A-Za-z0-9-]{10,}\b/g,
    explain: 'Matches the documented format of a Slack bot/user/app token (xoxb-/xoxp-/xoxa-/xoxr-/xoxs-).',
    benign: 'The workspace may have revoked it, or it may be an anonymised example copied from documentation.',
  },
  {
    id: 'google_api_key', severity: 'medium', label: 'Google API key format',
    re: /\bAIza[0-9A-Za-z_-]{35}\b/g,
    explain: 'Matches the documented format of a Google API key (AIza prefix + 35 characters).',
    benign: 'Many Google API keys are intentionally shipped in client apps and restricted by referrer/app — a match here is often by design.',
  },
  {
    id: 'sendgrid_key', severity: 'high', label: 'SendGrid API key format',
    re: /\bSG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}\b/g,
    explain: 'Matches the documented three-part format of a SendGrid API key (SG.xxxx.yyyy).',
    benign: 'The key may be deleted or scoped read-only; the format does not show its permissions.',
  },
  {
    id: 'twilio_key', severity: 'high', label: 'Twilio API key SID format',
    re: /\bSK[0-9a-fA-F]{32}\b/g,
    explain: 'Matches the format of a Twilio API key SID (SK + 32 hex characters).',
    benign: 'A SID identifies a key but is not the secret itself; it may also be an unrelated hex string that happens to start with SK.',
  },
];

const JWT_RE = /\beyJ[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\b/g;

// REAL decoding: only report a JWT if its first segment base64url-decodes to a
// JSON object with a string "alg" — this is what keeps eyJ-lookalikes out.
function jwtHeaderValid(token) {
  try {
    const seg = token.split('.')[0];
    let b64 = seg.replace(/-/g, '+').replace(/_/g, '/');
    while (b64.length % 4 !== 0) b64 += '=';
    const decoded = Buffer.from(b64, 'base64').toString('utf8');
    const obj = JSON.parse(decoded);
    return !!obj && typeof obj === 'object' && typeof obj.alg === 'string';
  } catch (e) {
    return false;
  }
}

const PEM_RE = /-----BEGIN [A-Z0-9 ]*PRIVATE KEY(?: BLOCK)?-----/;

const CONN_RE = /\b([a-z][a-z0-9+.-]{1,30}):\/\/([^\s:/@"']{1,64}):([^\s@/"']{1,128})@([^\s"']{1,200})/gi;

const GENERIC_RE = /([A-Za-z0-9_.-]*(?:secret|token|passw(?:or)?d|pwd|api[_-]?key|apikey|auth|credential)[A-Za-z0-9_.-]*)\s*[:=]\s*["']?([^\s"']{16,})/gi;
const GENERIC_ENTROPY_MIN = 3.5;

module.exports = {
  VENDOR,
  JWT_RE,
  jwtHeaderValid,
  PEM_RE,
  CONN_RE,
  GENERIC_RE,
  GENERIC_ENTROPY_MIN,
  isPlaceholder,
  shannonEntropy,
};
