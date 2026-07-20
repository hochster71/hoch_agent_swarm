// test/engine.test.js — HCF Secret & Key Exposure Scan — engine tests.
// Deterministic, offline, no install, no network, no keys.
'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const { scanText, previewText, MAX_CHARS } = require('../engine');
const { shannonEntropy } = require('../engine/entropy');
const { mask } = require('../engine/mask');
const { lintReport } = require('../engine/report_linter');

let pass = 0, fail = 0;
function t(name, fn) {
  try { fn(); pass += 1; console.log('  ok  ' + name); }
  catch (e) { fail += 1; console.error('  FAIL ' + name + '\n       ' + e.message); }
}
function throwsCode(fn, code) {
  try { fn(); } catch (e) { assert.strictEqual(e.code, code, 'expected ' + code + ' got ' + e.code); return; }
  throw new Error('expected throw ' + code + ', nothing thrown');
}

const SAMPLE = fs.readFileSync(path.join(__dirname, '..', 'engine', 'sample', 'sample_input.txt'), 'utf8').split('%%').join('');

// Synthetic fixtures (none are real credentials).
const AWS_KEY = 'AKIAQ2RT' + 'X7YB4KDM9WPU';
const GHP = 'ghp_Ab3d' + 'EfG7hIjK9LmNoPqRsTuVwXyZ012345ab';
const SK_LIVE = 'sk_live_' + 'a1B2c3D4e5F6g7H8i9J0k1L2';
const SK_TEST = 'rk_test_' + 'a1B2c3D4e5F6g7H8i9J0k1L2';
const WHSEC = 'whsec_a1' + 'B2c3D4e5F6g7H8i9J0';
const SLACK = 'xoxb-832' + '14567-QWErtyUIopASdfGHjkl';
const GOOGLE = 'AIzaSyD4' + 'kQ9mB2xW7vN1pLr8tYcE3hUj5oZa6fq';
const SENDGRID = 'SG.' + 'a1B2c3D4' + 'e5F6g7H8i9J0k1' + '.' + 'A1b2C3d4' + 'E5f6G7h8I9j0K1l2M3n4O5p6Q7r8S9t0U1v';
const TWILIO = 'SK012345' + '6789abcdef0123456789abcdef';
const HIGH_ENTROPY = 'Xk9mQ2vL7pR4wN8t';

function b64url(objOrStr) {
  const s = typeof objOrStr === 'string' ? objOrStr : JSON.stringify(objOrStr);
  return Buffer.from(s, 'utf8').toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
const JWT_VALID = b64url({ alg: 'HS256', typ: 'JWT' }) + '.' + b64url({ sub: '1234567890' }) + '.' + 'c2lnbmF0dXJl';
// Looks JWT-ish (eyJ...) but the header segment is NOT valid JSON when decoded.
const JWT_BOGUS = 'eyJhbGci.eyJhbGci.c2lnbmF0dXJl';

console.log('\nHCF Secret & Key Exposure Scan — engine tests (offline, deterministic)\n');

console.log('input validation');
t('empty input -> EMPTY_INPUT', () => throwsCode(() => scanText(''), 'EMPTY_INPUT'));
t('whitespace-only input -> EMPTY_INPUT', () => throwsCode(() => scanText('   \n \t '), 'EMPTY_INPUT'));
t('non-string input -> EMPTY_INPUT', () => throwsCode(() => scanText(null), 'EMPTY_INPUT'));
t('oversized input -> INPUT_TOO_LARGE', () => throwsCode(() => scanText('a'.repeat(MAX_CHARS + 1)), 'INPUT_TOO_LARGE'));
t('clean prose -> 0 findings, band LOW, disclaimer intact', () => {
  const r = scanText('The quick brown fox jumps over the lazy dog.\nNothing secret here.');
  assert.strictEqual(r.total, 0);
  assert.strictEqual(r.band, 'LOW');
  assert.ok(r.disclaimer.includes('NOT A GUARANTEE'));
  assert.ok(r.text.includes('NOT A GUARANTEE'));
});

console.log('\nentropy');
t('entropy of a single repeated char is 0', () => assert.strictEqual(shannonEntropy('aaaaaaaa'), 0));
t('entropy of 16 uniform distinct chars is exactly 4 bits/char', () => assert.strictEqual(shannonEntropy('0123456789abcdef'), 4));
t('random-looking value carries more entropy than a repeated one', () => {
  assert.ok(shannonEntropy(HIGH_ENTROPY) > shannonEntropy('abababababababab'));
});
t('empty string entropy is 0', () => assert.strictEqual(shannonEntropy(''), 0));

console.log('\nmasking guardrail');
t('mask keeps first 4 + last 2 for long values', () => {
  const m = mask(AWS_KEY);
  assert.ok(m.startsWith('AKIA'));
  assert.ok(m.endsWith('PU'));
  assert.ok(m.includes('•'));
});
t('mask fully hides short values', () => assert.strictEqual(mask('abc123'), '••••••'));
t('report JSON never contains the raw matched value', () => {
  const r = scanText('key=' + AWS_KEY + '\ntoken=' + GHP);
  const blob = JSON.stringify(r);
  assert.strictEqual(blob.includes(AWS_KEY), false);
  assert.strictEqual(blob.includes(GHP), false);
});

console.log('\nvendor detectors');
t('AWS AKIA key -> high, correct line', () => {
  const r = scanText('line one\nline two\nAWS_ACCESS_KEY_ID=' + AWS_KEY);
  assert.strictEqual(r.counts.high, 1);
  const f = r.findings[0];
  assert.strictEqual(f.detector, 'aws_access_key_id');
  assert.strictEqual(f.line, 3);
});
t('AWS ASIA (temporary credential) variant also matches', () => {
  const r = scanText('x=ASIA' + 'Q2RTX7YB4KDM9WPU');
  assert.strictEqual(r.findings[0].detector, 'aws_access_key_id');
});
t('GitHub ghp_ token -> high', () => {
  const r = scanText('GITHUB_TOKEN=' + GHP);
  assert.strictEqual(r.findings.length, 1);
  assert.strictEqual(r.findings[0].detector, 'github_token');
  assert.strictEqual(r.findings[0].severity, 'high');
});
t('Stripe live secret key -> high', () => {
  const r = scanText('STRIPE_KEY=' + SK_LIVE);
  assert.strictEqual(r.findings.length, 1);
  assert.strictEqual(r.findings[0].detector, 'stripe_live_key');
  assert.strictEqual(r.findings[0].severity, 'high');
});
t('Stripe TEST-mode key -> low severity (cannot move real money)', () => {
  const r = scanText('k=' + SK_TEST);
  assert.strictEqual(r.findings[0].detector, 'stripe_test_key');
  assert.strictEqual(r.findings[0].severity, 'low');
});
t('Stripe webhook signing secret -> high', () => {
  const r = scanText('x=' + WHSEC);
  assert.strictEqual(r.findings[0].detector, 'stripe_webhook_secret');
});
t('Slack xoxb token -> high', () => {
  const r = scanText('SLACK=' + SLACK);
  assert.strictEqual(r.findings[0].detector, 'slack_token');
});
t('Google API key -> medium (often shipped client-side by design)', () => {
  const r = scanText('maps_key: ' + GOOGLE);
  assert.strictEqual(r.findings[0].detector, 'google_api_key');
  assert.strictEqual(r.findings[0].severity, 'medium');
});
t('SendGrid three-part key -> high', () => {
  const r = scanText('SG_KEY=' + SENDGRID);
  assert.strictEqual(r.findings[0].detector, 'sendgrid_key');
});
t('Twilio SK hex SID -> high', () => {
  const r = scanText('twilio=' + TWILIO);
  assert.strictEqual(r.findings[0].detector, 'twilio_key');
});
t('vendor match whose value is a placeholder is SUPPRESSED, not reported', () => {
  const r = scanText('w=whsec_REPLACEMEREPLACEME');
  assert.strictEqual(r.total, 0);
  assert.strictEqual(r.suppressed.count, 1);
  assert.strictEqual(r.suppressed.reasons.placeholder, 1);
});

console.log('\njwt (real header decoding)');
t('structurally valid JWT with decodable {"alg":...} header -> medium', () => {
  const r = scanText('Authorization: Bearer ' + JWT_VALID);
  assert.strictEqual(r.findings.length, 1);
  assert.strictEqual(r.findings[0].detector, 'jwt');
  assert.strictEqual(r.findings[0].severity, 'medium');
});
t('eyJ-lookalike whose header does NOT decode to JSON is ignored', () => {
  const r = scanText('x=' + JWT_BOGUS);
  assert.strictEqual(r.total, 0);
});

console.log('\nprivate key blocks');
t('RSA PRIVATE KEY begin marker -> high, on the marker line', () => {
  const r = scanText('before\n-----BEGIN RSA PRIVATE KEY-----\nMIIEow\n-----END RSA PRIVATE KEY-----');
  assert.strictEqual(r.findings.length, 1);
  assert.strictEqual(r.findings[0].detector, 'private_key_block');
  assert.strictEqual(r.findings[0].line, 2);
});
t('OPENSSH PRIVATE KEY variant matches', () => {
  const r = scanText('-----BEGIN OPENSSH PRIVATE KEY-----');
  assert.strictEqual(r.findings[0].detector, 'private_key_block');
});
t('key-block body/base64 material is never reproduced in the report', () => {
  const body = 'MIIEowIBAAKCAQEA0synthetickeymaterial0000';
  const r = scanText('-----BEGIN RSA PRIVATE KEY-----\n' + body + '\n-----END RSA PRIVATE KEY-----');
  assert.strictEqual(JSON.stringify(r).includes(body), false);
});

console.log('\nconnection strings');
t('postgres://user:pass@host -> high, password masked', () => {
  const r = scanText('DATABASE_URL=postgres://svc_app:vN8kQz42hTr9wLmX@db.host:5432/app');
  assert.strictEqual(r.findings.length, 1);
  const f = r.findings[0];
  assert.strictEqual(f.detector, 'connection_string_password');
  assert.strictEqual(f.severity, 'high');
  assert.strictEqual(JSON.stringify(r).includes('vN8kQz42hTr9wLmX'), false);
  assert.ok(f.masked.startsWith('postgres://svc_app:'));
});
t('connection string with ${VAR} placeholder password is suppressed', () => {
  const r = scanText('DATABASE_URL=postgres://svc_app:${DB_PASS}@db.host:5432/app');
  assert.strictEqual(r.total, 0);
  assert.strictEqual(r.suppressed.reasons.placeholder, 1);
});
t('plain URL with no user:pass is not flagged', () => {
  const r = scanText('homepage=https://docs.hoch.example/path?q=1');
  assert.strictEqual(r.total, 0);
});

console.log('\ngeneric named-secret assignments');
t('secret-like name + high-entropy value -> medium, name recorded', () => {
  const r = scanText('SESSION_PASSWORD=' + HIGH_ENTROPY);
  assert.strictEqual(r.findings.length, 1);
  const f = r.findings[0];
  assert.strictEqual(f.detector, 'named_secret_assignment');
  assert.strictEqual(f.severity, 'medium');
  assert.strictEqual(f.name, 'SESSION_PASSWORD');
});
t('placeholder value (changeme) is suppressed with reason', () => {
  const r = scanText('password=changeme_changeme');
  assert.strictEqual(r.total, 0);
  assert.strictEqual(r.suppressed.reasons.placeholder, 1);
});
t('low-entropy value is suppressed with reason', () => {
  const r = scanText('password=aaaaaaaaaaaaaaaaaa');
  assert.strictEqual(r.total, 0);
  assert.strictEqual(r.suppressed.reasons.low_entropy, 1);
});
t('env-var reference value ($NAME) is suppressed as placeholder', () => {
  const r = scanText('DB_PASSWORD=$PRODUCTION_DB_PASSWORD');
  assert.strictEqual(r.total, 0);
  assert.strictEqual(r.suppressed.reasons.placeholder, 1);
});
t('short value (<16 chars) on a secret-like name is not flagged', () => {
  const r = scanText('password=hunter2now');
  assert.strictEqual(r.total, 0);
  assert.strictEqual(r.suppressed.count, 0);
});
t('vendor match is NOT double-reported by the generic detector (span claim)', () => {
  const r = scanText('STRIPE_SECRET_KEY=' + SK_LIVE);
  assert.strictEqual(r.findings.length, 1);
  assert.strictEqual(r.findings[0].detector, 'stripe_live_key');
});
t('suppressed counts are disclosed in the report and rendered text', () => {
  const r = scanText('a=whsec_REPLACEMEREPLACEME\npassword=aaaaaaaaaaaaaaaaaa');
  assert.strictEqual(r.suppressed.count, 2);
  assert.ok(r.text.includes('Set aside as likely placeholders or low-entropy values: 2'));
});

console.log('\nlines, counts, band');
t('CRLF input still reports the right line number', () => {
  const r = scanText('one\r\ntwo\r\nkey=' + AWS_KEY);
  assert.strictEqual(r.findings[0].line, 3);
});
t('multiple findings are sorted by line then column', () => {
  const r = scanText('t=' + GHP + '\nk=' + AWS_KEY);
  assert.strictEqual(r.findings[0].line, 1);
  assert.strictEqual(r.findings[1].line, 2);
});
t('counts tally the findings exactly', () => {
  const r = scanText('k=' + AWS_KEY + '\ng=' + GOOGLE + '\nt=' + SK_TEST);
  assert.deepStrictEqual(r.counts, { high: 1, medium: 1, low: 1 });
  assert.strictEqual(r.total, 3);
});
t('band HIGH when any high-severity signal exists', () => {
  const r = scanText('k=' + AWS_KEY + '\ng=' + GOOGLE);
  assert.strictEqual(r.band, 'HIGH');
});
t('band ELEVATED when only medium signals exist', () => {
  const r = scanText('g=' + GOOGLE);
  assert.strictEqual(r.band, 'ELEVATED');
});
t('band LOW when only low/no signals exist', () => {
  const r = scanText('t=' + SK_TEST);
  assert.strictEqual(r.band, 'LOW');
});

console.log('\nrender + guardrail linter (fail-closed)');
t('rendered text carries every masked finding and the disclaimer', () => {
  const r = scanText('k=' + AWS_KEY);
  assert.ok(r.text.includes('[HIGH] line 1'));
  assert.ok(r.text.includes('NOT A GUARANTEE'));
});
t('every finding carries a non-empty benign explanation', () => {
  const r = scanText(SAMPLE);
  for (const f of r.findings) assert.ok(f.benign && f.benign.trim().length > 10, f.detector);
});
t('linter throws on a seeded certainty over-claim', () => {
  const r = scanText('k=' + AWS_KEY);
  const bad = JSON.parse(JSON.stringify(r));
  bad.findings[0].explain = 'This key is definitely exposed.';
  throwsCode(() => lintReport(bad), 'REPORT_LINTER_FAILED');
});
t('linter throws on a seeded security directive', () => {
  const r = scanText('k=' + AWS_KEY);
  const bad = JSON.parse(JSON.stringify(r));
  bad.findings[0].benign = 'You must rotate this credential.';
  throwsCode(() => lintReport(bad), 'REPORT_LINTER_FAILED');
});
t('linter throws on a seeded safety assurance', () => {
  const r = scanText('t=' + SK_TEST);
  const bad = JSON.parse(JSON.stringify(r));
  bad.summary = 'There is no risk in this file.';
  throwsCode(() => lintReport(bad), 'REPORT_LINTER_FAILED');
});
t('linter throws when the disclaimer is stripped', () => {
  const r = scanText('k=' + AWS_KEY);
  const bad = JSON.parse(JSON.stringify(r));
  bad.disclaimer = 'all good';
  throwsCode(() => lintReport(bad), 'REPORT_LINTER_FAILED');
});
t('linter throws when a finding loses its benign explanation', () => {
  const r = scanText('k=' + AWS_KEY);
  const bad = JSON.parse(JSON.stringify(r));
  bad.findings[0].benign = '';
  throwsCode(() => lintReport(bad), 'REPORT_LINTER_FAILED');
});

console.log('\ndeterminism + robustness');
t('same input -> byte-identical report JSON', () => {
  assert.strictEqual(JSON.stringify(scanText(SAMPLE)), JSON.stringify(scanText(SAMPLE)));
});
t('hostile regex-special input does not crash and stays linted', () => {
  const r = scanText('(((***)))\\\\ $$$ [a-z]+ {16,} ??? \n key=' + AWS_KEY);
  assert.strictEqual(r.total, 1);
});

console.log('\nfree preview subset');
t('preview returns locked counts only', () => {
  const p = previewText(SAMPLE);
  assert.strictEqual(p.locked, true);
  assert.ok(p.counts.high >= 1);
  assert.strictEqual(p.findings, undefined);
});
t('preview JSON leaks no masked values, detectors, or line numbers', () => {
  const blob = JSON.stringify(previewText(SAMPLE));
  assert.strictEqual(blob.includes('masked'), false);
  assert.strictEqual(blob.includes('aws_access_key_id'), false);
  assert.strictEqual(blob.includes('"line"'), false);
  assert.strictEqual(blob.includes('•'), false);
});
t('preview on clean text -> zero counts, band LOW', () => {
  const p = previewText('nothing to see here at all');
  assert.deepStrictEqual(p.counts, { high: 0, medium: 0, low: 0 });
  assert.strictEqual(p.band, 'LOW');
});

console.log('\nsample file (the demo the buyer sees)');
t('sample scan -> 5 high, 3 medium, 1 suppressed, band HIGH', () => {
  const r = scanText(SAMPLE);
  assert.strictEqual(r.counts.high, 5);
  assert.strictEqual(r.counts.medium, 3);
  assert.strictEqual(r.counts.low, 0);
  assert.strictEqual(r.suppressed.count, 1);
  assert.strictEqual(r.band, 'HIGH');
});
t('sample scan finds the PEM block on its BEGIN line (8)', () => {
  const r = scanText(SAMPLE);
  const pem = r.findings.find((f) => f.detector === 'private_key_block');
  assert.strictEqual(pem.line, 8);
});
t('sample raw secrets never appear in the report JSON', () => {
  const r = scanText(SAMPLE);
  const blob = JSON.stringify(r);
  assert.strictEqual(blob.includes('AKIAQ2RTX7YB4KDM9WPU'), false);
  assert.strictEqual(blob.includes('vN8kQz42hTr9wLmX'), false);
});

console.log(`\nengine: ${pass} passed, ${fail} failed\n`);
process.exit(fail === 0 ? 0 : 1);
