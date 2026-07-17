// test/engine.test.js
//
// HCF — Link & QR Safety Report — ENGINE tests (pure Node, no framework).
// Proves the offline heuristics genuinely fire on known-bad patterns, stay quiet
// on clean links, and that the guardrail (heuristic-only, mandatory disclaimer,
// no certainty) holds. Run: node test/engine.test.js

'use strict';

const assert = require('assert');
const { generateSafetyReport, DISCLAIMER } = require('../engine');
const { analyzeHost } = require('../engine/homoglyph');
const { classifyPayload } = require('../engine/qr');
const { lintReport, ReportLintError } = require('../engine/report_linter');

let pass = 0, fail = 0;
function ok(name, fn) {
  try { fn(); console.log('  PASS  ' + name); pass++; }
  catch (e) { console.log('  FAIL  ' + name + '  -> ' + e.message); fail++; }
}
function hasFinding(report, id) { return report.findings.some((f) => f.id === id); }

console.log('HCF Link & QR Safety Report — engine tests\n');

// --- Clean, ordinary https link: LOW band, still disclaimed, never "safe" ---
ok('clean https brand URL -> LOW band + mandatory disclaimer', () => {
  const r = generateSafetyReport({ input: 'https://www.google.com/search?q=cats' });
  assert.strictEqual(r.band, 'LOW', 'expected LOW, got ' + r.band);
  assert.ok(r.disclaimer && r.disclaimer.length > 20, 'disclaimer present');
  assert.ok(!/\bis\s+safe\b/i.test(r.text), 'must never say the link IS safe');
});

// --- http (no TLS) surfaces the no_tls signal ---
ok('http:// surfaces a no-TLS signal', () => {
  const r = generateSafetyReport({ input: 'http://example.com/login' });
  assert.ok(hasFinding(r, 'no_tls'), 'expected no_tls finding');
});

// --- Raw IP host -> HIGH ---
ok('raw IP host -> ip_host + HIGH band', () => {
  const r = generateSafetyReport({ input: 'http://192.168.10.5/verify' });
  assert.ok(hasFinding(r, 'ip_host'), 'expected ip_host');
  assert.strictEqual(r.band, 'HIGH');
});

// --- Credentials/@ trick -> userinfo_in_url HIGH ---
ok('"@"-in-authority trick -> userinfo_in_url HIGH', () => {
  const r = generateSafetyReport({ input: 'https://paypal.com@evil.example.tk/login' });
  assert.ok(hasFinding(r, 'userinfo_in_url'), 'expected userinfo_in_url');
  assert.strictEqual(r.band, 'HIGH');
});

// --- Punycode host detected ---
ok('punycode host (xn--) detected', () => {
  const r = generateSafetyReport({ input: 'https://xn--pple-43d.com/login' });
  assert.ok(hasFinding(r, 'punycode_host'), 'expected punycode_host');
});

// --- Cyrillic homoglyph host detected as mixed-script ---
ok('cyrillic homoglyph host -> homoglyph_mixed_script', () => {
  // "аpple.com" with a Cyrillic 'а'
  const r = generateSafetyReport({ input: 'https://аpple.com/login' });
  assert.ok(hasFinding(r, 'homoglyph_mixed_script'), 'expected homoglyph_mixed_script');
  assert.strictEqual(r.band, 'HIGH');
});

// --- Brand lookalike (paypal token on a non-paypal registrable domain) ---
ok('brand lookalike -> brand_lookalike HIGH', () => {
  const r = generateSafetyReport({ input: 'https://paypal.account-verify.com/login' });
  assert.ok(hasFinding(r, 'brand_lookalike'), 'expected brand_lookalike');
  assert.strictEqual(r.band, 'HIGH');
});

// --- Official brand domain does NOT trip brand_lookalike ---
ok('official paypal.com does NOT trip brand_lookalike', () => {
  const r = generateSafetyReport({ input: 'https://www.paypal.com/signin' });
  assert.ok(!hasFinding(r, 'brand_lookalike'), 'official domain should not be a lookalike');
});

// --- Suspicious TLD ---
ok('abused TLD (.zip) -> suspicious_tld', () => {
  const r = generateSafetyReport({ input: 'https://invoice-update.zip/' });
  assert.ok(hasFinding(r, 'suspicious_tld'), 'expected suspicious_tld');
});

// --- Shortener flags unresolved destination ---
ok('shortener -> shortener signal (destination unresolved offline)', () => {
  const r = generateSafetyReport({ input: 'https://bit.ly/3xyzABC' });
  assert.ok(hasFinding(r, 'shortener'), 'expected shortener');
  assert.ok(/UNRESOLVED/i.test(r.text), 'must state destination unresolved');
});

// --- Embedded open-redirect target is walked and surfaced ---
ok('embedded redirect target is extracted and analyzed', () => {
  const r = generateSafetyReport({ input: 'https://safe.example.com/out?url=https://paypal.login-secure.tk/x' });
  assert.ok(r.redirectChainStatic.length >= 2, 'expected a static redirect chain >= 2');
  assert.ok(hasFinding(r, 'embedded_redirect'), 'expected embedded_redirect');
  assert.ok(r.findings.some((f) => /^nested_/.test(f.id)), 'expected nested target findings');
});

// --- Risky executable path ---
ok('direct .exe download -> risky_extension', () => {
  const r = generateSafetyReport({ input: 'http://download.example.top/setup.exe' });
  assert.ok(hasFinding(r, 'risky_extension'), 'expected risky_extension');
});

// --- Defanged threat-intel format is normalized ---
ok('defanged "hxxp" + "[.]" input is normalized and parsed', () => {
  const r = generateSafetyReport({ input: 'hxxp://evil[.]example[.]tk/login' });
  assert.strictEqual(r.normalizedUrl, 'http://evil.example.tk/login');
});

// --- QR payload classification ---
ok('QR wifi payload classified, not URL-analyzed', () => {
  const r = generateSafetyReport({ kind: 'qr', input: 'WIFI:T:WPA;S:HomeNet;P:secret123;;' });
  assert.strictEqual(r.payload.kind, 'wifi');
  assert.strictEqual(r.normalizedUrl, null);
});
ok('QR url payload routes into URL heuristics', () => {
  const r = generateSafetyReport({ kind: 'qr', input: 'https://paypal.account-verify.com/login' });
  assert.strictEqual(r.payload.kind, 'url');
  assert.ok(hasFinding(r, 'brand_lookalike'), 'QR url should be heuristically analyzed');
});
ok('classifyPayload recognizes otp/mailto/tel/geo', () => {
  assert.strictEqual(classifyPayload('otpauth://totp/x').kind, 'otp');
  assert.strictEqual(classifyPayload('mailto:a@b.com').kind, 'email');
  assert.strictEqual(classifyPayload('tel:+15551234').kind, 'phone');
  assert.strictEqual(classifyPayload('geo:1,2').kind, 'geo');
});

// --- homoglyph analyzer unit behavior ---
ok('analyzeHost flags cyrillic confusables and mixed script', () => {
  const a = analyzeHost('аpple.com'); // cyrillic a
  assert.strictEqual(a.mixedScript, true);
  assert.ok(a.confusables.length >= 1);
  const b = analyzeHost('apple.com');
  assert.strictEqual(b.mixedScript, false);
});

// --- report linter fails closed on a certainty over-claim ---
ok('report-linter THROWS on a certainty over-claim', () => {
  let threw = null;
  try {
    lintReport({ disclaimer: DISCLAIMER }, 'This link is safe, guaranteed safe.');
  } catch (e) { threw = e; }
  assert.ok(threw instanceof ReportLintError, 'expected ReportLintError');
});
ok('report-linter THROWS when disclaimer missing', () => {
  let threw = null;
  try { lintReport({ disclaimer: '' }, 'ordinary text'); } catch (e) { threw = e; }
  assert.ok(threw instanceof ReportLintError, 'expected ReportLintError');
});

// --- unparseable input raises a clean error, not a fake report ---
ok('empty input throws (no fake report)', () => {
  let threw = null;
  try { generateSafetyReport({ input: '   ' }); } catch (e) { threw = e; }
  assert.ok(threw && (threw.code === 'EMPTY_INPUT' || threw.code === 'UNPARSEABLE_URL'), 'expected parse error');
});

// --- every generated report carries the exact disclaimer text ---
ok('every report embeds the mandatory disclaimer verbatim', () => {
  const r = generateSafetyReport({ input: 'https://example.com' });
  assert.strictEqual(r.disclaimer, DISCLAIMER);
  assert.ok(r.text.includes(DISCLAIMER), 'rendered text must include disclaimer');
});

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail === 0 ? 0 : 1);
