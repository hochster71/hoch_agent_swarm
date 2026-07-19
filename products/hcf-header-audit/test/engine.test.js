// test/engine.test.js — HCF Email Header Audit — engine tests.
// Dependency-free. Run: node test/engine.test.js
'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const { auditHeaders, previewHeaders } = require('../engine');
const { parseHeaderBlock, decodeEncodedWords, getAll } = require('../engine/parse_headers');
const { parseAddressList, firstAddress, registrableDomain } = require('../engine/addresses');
const { analyzeDomain, foldConfusables } = require('../engine/lookalike');
const { parseAuthResultsValue, collectAuthResults } = require('../engine/auth_results');
const { buildChain, isPrivateIp } = require('../engine/hops');
const { scoreFindings } = require('../engine/score');
const { lintReport, ReportLintError } = require('../engine/report_linter');

let pass = 0, fail = 0;
function t(name, fn) {
  try { fn(); pass += 1; console.log('  ok  ' + name); }
  catch (e) { fail += 1; console.error('  FAIL ' + name + '\n       ' + e.message); }
}

const SAMPLE = fs.readFileSync(path.join(__dirname, '..', 'engine', 'sample', 'sample_headers.txt'), 'utf8');
const CLEAN = [
  'Received: from mail.vendor.com (mail.vendor.com [203.0.113.5]) by mx.corp.example with ESMTPS id aa; Tue, 14 Jul 2026 09:00:10 +0000',
  'Received: from send.vendor.com (send.vendor.com [203.0.113.4]) by mail.vendor.com with ESMTPS id bb; Tue, 14 Jul 2026 09:00:00 +0000',
  'Authentication-Results: mx.corp.example; spf=pass smtp.mailfrom=notify@vendor.com; dkim=pass header.d=vendor.com; dmarc=pass header.from=vendor.com',
  'From: Vendor Notifications <notify@vendor.com>',
  'To: alex@corp.example',
  'Subject: Your weekly summary',
  'Date: Tue, 14 Jul 2026 09:00:00 +0000',
  'Message-ID: <abc123@vendor.com>',
].join('\n');

console.log('\nHCF Email Header Audit — engine tests\n');

// --- header parsing -------------------------------------------------------
console.log('header parsing');
t('parses simple headers', () => {
  const r = parseHeaderBlock('From: a@b.com\nSubject: hi\n');
  assert.strictEqual(r.headers.length, 2);
  assert.strictEqual(r.headers[0].nameLower, 'from');
});
t('unfolds continuation lines', () => {
  const r = parseHeaderBlock('Subject: hello\n  world\n\tagain\n');
  assert.strictEqual(r.headers[0].value, 'hello world again');
});
t('handles CRLF line endings', () => {
  const r = parseHeaderBlock('From: a@b.com\r\nSubject: hi\r\n');
  assert.strictEqual(r.headers.length, 2);
});
t('strips a UTF-8 BOM', () => {
  const r = parseHeaderBlock('﻿From: a@b.com\n');
  assert.strictEqual(r.headers[0].nameLower, 'from');
});
t('stops at the blank line and flags that a body followed', () => {
  const r = parseHeaderBlock('From: a@b.com\n\nthis is the body\n');
  assert.strictEqual(r.headers.length, 1);
  assert.strictEqual(r.truncatedAtBody, true);
});
t('records malformed lines with line numbers instead of dropping them', () => {
  const r = parseHeaderBlock('From: a@b.com\nnot a header\nTo: c@d.com\n');
  assert.strictEqual(r.malformed.length, 1);
  assert.strictEqual(r.malformed[0].line, 2);
});
t('preserves duplicate Received headers in order', () => {
  const r = parseHeaderBlock('Received: one\nReceived: two\nFrom: a@b.com\n');
  assert.deepStrictEqual(getAll(r.headers, 'received'), ['one', 'two']);
});
t('decodes RFC2047 base64 and quoted-printable words', () => {
  assert.strictEqual(decodeEncodedWords('=?utf-8?B?SsO2cmc=?='), 'Jörg');
  assert.strictEqual(decodeEncodedWords('=?utf-8?Q?Hi_there?='), 'Hi there');
});
t('throws a coded error on empty input', () => {
  assert.throws(() => parseHeaderBlock('   '), (e) => e.code === 'EMPTY_INPUT');
});
t('throws a coded error when nothing parses as a header', () => {
  assert.throws(() => parseHeaderBlock('just some prose\nmore prose'), (e) => e.code === 'NO_HEADERS');
});
t('rejects oversized input', () => {
  assert.throws(() => parseHeaderBlock('From: a@b.com\n' + 'x'.repeat(300 * 1024)), (e) => e.code === 'INPUT_TOO_LARGE');
});

// --- addresses ------------------------------------------------------------
console.log('\naddresses & domains');
t('takes the real address, not one hidden in a quoted display name', () => {
  const a = firstAddress('"PayPal <service@paypal.com>" <billing@evil.example>');
  assert.strictEqual(a.address, 'billing@evil.example');
  assert.strictEqual(a.domain, 'evil.example');
});
t('parses a plain address', () => {
  assert.strictEqual(firstAddress('plain@b.com').address, 'plain@b.com');
});
t('parses a parenthesised comment as the display name', () => {
  const a = firstAddress('b@c.com (Bob)');
  assert.strictEqual(a.display, 'Bob');
  assert.strictEqual(a.address, 'b@c.com');
});
t('splits an address list without breaking on commas inside quotes', () => {
  const l = parseAddressList('"Smith, Jane" <j@a.com>, bob@b.com');
  assert.strictEqual(l.length, 2);
  assert.strictEqual(l[0].address, 'j@a.com');
});
t('reduces multi-label public suffixes correctly', () => {
  assert.strictEqual(registrableDomain('mail.foo.co.uk'), 'foo.co.uk');
  assert.strictEqual(registrableDomain('a.b.example.com'), 'example.com');
  assert.strictEqual(registrableDomain('example.com'), 'example.com');
});
t('marks an address with no @ as invalid', () => {
  assert.strictEqual(firstAddress('notanaddress').valid, false);
});

// --- lookalike ------------------------------------------------------------
console.log('\nlookalike detection');
t('folds confusable characters', () => {
  assert.strictEqual(foldConfusables('paypa1'), 'paypal');
  assert.strictEqual(foldConfusables('micros0ft'), 'microsoft');
});
t('flags a character-substituted brand domain', () => {
  assert.strictEqual(analyzeDomain('paypa1.com').confusable.length > 0, true);
});
t('flags a brand name on someone else\'s registrable domain', () => {
  assert.strictEqual(analyzeDomain('paypal.secure-login.example.net').brandAdjacent.length > 0, true);
});
t('flags a substituted brand inside a longer label', () => {
  assert.strictEqual(analyzeDomain('paypa1-billing.example').brandAdjacent.length > 0, true);
});
t('flags punycode domains', () => {
  assert.strictEqual(analyzeDomain('xn--pypal-4ve.com').punycode, true);
});
t('does NOT flag the genuine brand domain', () => {
  const a = analyzeDomain('paypal.com');
  assert.strictEqual(a.confusable.length, 0);
  assert.strictEqual(a.brandAdjacent.length, 0);
});
t('does NOT flag legitimate brand subdomains', () => {
  for (const d of ['mail.google.com', 'em1234.netflix.com', 'notifications.stripe.com']) {
    const a = analyzeDomain(d);
    assert.strictEqual(a.confusable.length + a.brandAdjacent.length, 0, d + ' produced a false positive');
  }
});

// --- auth results ---------------------------------------------------------
console.log('\nauthentication results');
t('parses methods and properties out of Authentication-Results', () => {
  const p = parseAuthResultsValue('mx.a.com; spf=pass smtp.mailfrom=x@b.com; dkim=fail header.d=c.com; dmarc=pass header.from=b.com');
  assert.strictEqual(p.authservId, 'mx.a.com');
  assert.strictEqual(p.results.length, 3);
  assert.strictEqual(p.results[0].result, 'pass');
  assert.strictEqual(p.results[1].headerD, 'c.com');
});
t('prefers the nearest non-ARC block and records every authserv-id', () => {
  const { headers } = parseHeaderBlock([
    'Authentication-Results: mx.mine.com; dkim=pass header.d=a.com',
    'ARC-Authentication-Results: i=1; relay.com; dkim=fail',
    'Authentication-Results: relay.com; dkim=fail header.d=a.com',
    'From: a@a.com',
  ].join('\n'));
  const c = collectAuthResults(headers);
  assert.strictEqual(c.byMethod.dkim.result, 'pass');
  assert.strictEqual(c.authservIds.length, 2);
});
t('falls back to Received-SPF when no Authentication-Results exists', () => {
  const { headers } = parseHeaderBlock('Received-SPF: Fail (domain does not designate)\nFrom: a@b.com\n');
  const c = collectAuthResults(headers);
  assert.strictEqual(c.byMethod.spf.result, 'fail');
  assert.strictEqual(c.present, true);
});

// --- hops -----------------------------------------------------------------
console.log('\ndelivery path');
t('orders hops oldest-first and identifies the origin', () => {
  const c = buildChain([
    'from b.com by c.com; Tue, 14 Jul 2026 10:05:00 +0000',
    'from a.com by b.com; Tue, 14 Jul 2026 10:00:00 +0000',
  ]);
  assert.strictEqual(c.origin.from, 'a.com');
  assert.strictEqual(c.hops[0].position, 1);
  assert.strictEqual(c.totalTransitMs, 300000);
});
t('extracts public IPs and excludes private ranges', () => {
  const c = buildChain(['from a.com (a.com [10.0.0.5]) by b.com; Tue, 14 Jul 2026 10:00:00 +0000']);
  assert.strictEqual(c.hops[0].ips.includes('10.0.0.5'), true);
  assert.strictEqual(c.hops[0].publicIps.length, 0);
});
t('classifies private IP ranges', () => {
  assert.ok(isPrivateIp('192.168.1.1') && isPrivateIp('172.16.0.1') && isPrivateIp('127.0.0.1'));
  assert.ok(!isPrivateIp('203.0.113.9'));
});
t('counts backwards-running timestamps as out of order', () => {
  const c = buildChain([
    'from b.com by c.com; Tue, 14 Jul 2026 09:00:00 +0000',
    'from a.com by b.com; Tue, 14 Jul 2026 10:00:00 +0000',
  ]);
  assert.strictEqual(c.outOfOrder, 1);
});
t('detects TLS mentions', () => {
  assert.strictEqual(buildChain(['from a by b with ESMTPS; Tue, 14 Jul 2026 10:00:00 +0000']).anyTls, true);
});

// --- scoring --------------------------------------------------------------
console.log('\nscoring');
t('scores an empty finding set as LOW', () => {
  const s = scoreFindings([]);
  assert.strictEqual(s.band, 'LOW');
  assert.strictEqual(s.score, 0);
});
t('info findings add no score', () => {
  assert.strictEqual(scoreFindings([{ severity: 'info' }, { severity: 'info' }]).score, 0);
});
t('bands escalate with severity and score is capped at 100', () => {
  assert.strictEqual(scoreFindings([{ severity: 'medium' }, { severity: 'low' }]).band, 'MODERATE');
  assert.strictEqual(scoreFindings([{ severity: 'high' }, { severity: 'high' }]).band, 'ELEVATED');
  const many = new Array(20).fill({ severity: 'high' });
  assert.strictEqual(scoreFindings(many).score, 100);
});

// --- guardrail linter -----------------------------------------------------
console.log('\nguardrail linter (fail-closed)');
t('rejects a report with no disclaimer', () => {
  assert.throws(() => lintReport({ disclaimer: '' }, 'text'), ReportLintError);
});
t('rejects a certainty over-claim', () => {
  assert.throws(() => lintReport({ disclaimer: 'd' }, 'This email is safe.'), (e) => e.code === 'REPORT_LINTER_FAILED');
  assert.throws(() => lintReport({ disclaimer: 'd' }, 'It is 100% phishing'), ReportLintError);
  assert.throws(() => lintReport({ disclaimer: 'd' }, 'confirmed malicious'), ReportLintError);
});
t('rejects a security directive', () => {
  assert.throws(() => lintReport({ disclaimer: 'd' }, 'You should delete this immediately'), ReportLintError);
  assert.throws(() => lintReport({ disclaimer: 'd' }, 'It is safe to click.'), ReportLintError);
});
t('accepts compliant observational text', () => {
  assert.strictEqual(lintReport({ disclaimer: 'd' }, 'SPF reported as fail. Benign explanations exist.'), true);
});

// --- end to end -----------------------------------------------------------
console.log('\nend-to-end audit');
t('audits the bundled spoof sample and reaches ELEVATED', () => {
  const r = auditHeaders(SAMPLE);
  assert.strictEqual(r.band, 'ELEVATED');
  assert.ok(r.findings.length >= 5);
});
t('resolves the real sender behind a decoy display name', () => {
  const r = auditHeaders(SAMPLE);
  assert.strictEqual(r.identity.fromDomain, 'paypa1-billing.example');
  assert.ok(r.findings.some((f) => f.id === 'display_name_address'));
});
t('surfaces reported auth failures without re-verifying them', () => {
  const r = auditHeaders(SAMPLE);
  assert.strictEqual(r.auth.reported.dmarc.result, 'fail');
  // The note must frame results as a server's claim AND disclaim verification.
  assert.ok(/WROTE/.test(r.auth.note), 'note must frame results as a server claim');
  assert.ok(/re-verified/i.test(r.auth.note), 'note must disclaim re-verification');
});
t('a clean vendor message lands in LOW with no high-severity signals', () => {
  const r = auditHeaders(CLEAN);
  assert.strictEqual(r.band, 'LOW');
  assert.strictEqual(r.counts.high, 0);
});
t('every report carries the mandatory disclaimer', () => {
  for (const src of [SAMPLE, CLEAN]) {
    assert.ok(auditHeaders(src).disclaimer.includes('NOT A GUARANTEE'));
  }
});
t('rendered text includes identity, path, signals and disclaimer sections', () => {
  const txt = auditHeaders(SAMPLE).text;
  for (const section of ['MESSAGE IDENTITY', 'DELIVERY PATH', 'SIGNALS', 'DISCLAIMER', 'ATTENTION BAND']) {
    assert.ok(txt.includes(section), 'missing section: ' + section);
  }
});
t('findings are sorted with high severity first', () => {
  const f = auditHeaders(SAMPLE).findings;
  const order = { high: 0, medium: 1, low: 2, info: 3 };
  for (let i = 1; i < f.length; i += 1) {
    assert.ok(order[f[i - 1].severity] <= order[f[i].severity], 'findings out of severity order');
  }
});
t('output is deterministic apart from the timestamp', () => {
  const a = auditHeaders(SAMPLE);
  const b = auditHeaders(SAMPLE);
  const strip = (r) => JSON.stringify(Object.assign({}, r, { generatedAt: null, text: r.text.replace(/\d{4}-\d\d-\d\dT[\d:.]+Z/g, '') }));
  assert.strictEqual(strip(a), strip(b));
});
t('preview exposes counts but never the finding details', () => {
  const p = previewHeaders(SAMPLE);
  const blob = JSON.stringify(p);
  assert.strictEqual(p.counts.high >= 1, true);
  assert.strictEqual(p.locked, true);
  assert.strictEqual(blob.includes('display_name_address'), false);
  assert.strictEqual(blob.includes('Display name shows'), false);
});
t('preview still carries the disclaimer', () => {
  assert.ok(previewHeaders(SAMPLE).disclaimer.includes('NOT A GUARANTEE'));
});
t('a partial paste with only a From line still audits', () => {
  const r = auditHeaders('From: someone@example.org');
  assert.ok(r.findings.some((f) => f.id === 'no_received'));
  assert.ok(r.findings.some((f) => f.id === 'no_auth_results'));
});
t('malformed lines are reported in the audit, not swallowed', () => {
  const r = auditHeaders('From: a@b.com\nthis is not a header\nSubject: x');
  assert.strictEqual(r.skippedLines.length, 1);
  assert.ok(r.findings.some((f) => f.id === 'malformed_lines'));
});

console.log(`\nengine: ${pass} passed, ${fail} failed\n`);
process.exit(fail === 0 ? 0 : 1);
