// engine/index.js
//
// HCF — Email Header Audit — engine orchestrator (OFFLINE, deterministic).
//
//   auditHeaders(rawHeaderText) -> full structured report + rendered text
//   previewHeaders(rawHeaderText) -> free, ungated identity summary + signal
//                                    COUNTS only (no finding details)
//
// No network is ever used: nothing is resolved in DNS, no message body is read,
// nothing is re-verified. The report ALWAYS carries the mandatory disclaimer and
// a fail-closed linter runs before it is returned.
'use strict';

const { parseHeaderBlock, getAll, getOne, HeaderParseError } = require('./parse_headers');
const { firstAddress, registrableDomain } = require('./addresses');
const { collectAuthResults } = require('./auth_results');
const { buildChain } = require('./hops');
const { runAllChecks } = require('./checks');
const { scoreFindings } = require('./score');
const { lintReport } = require('./report_linter');
const { PRODUCT_NAME, PRODUCT_SLUG, DISCLAIMER } = require('./constants');

const SEVERITY_ORDER = { high: 0, medium: 1, low: 2, info: 3 };

function buildContext(rawHeaderText) {
  const parsed = parseHeaderBlock(rawHeaderText);
  const H = parsed.headers;

  const headerIndex = {
    from: getOne(H, 'from'),
    to: getOne(H, 'to'),
    cc: getOne(H, 'cc'),
    subject: getOne(H, 'subject'),
    date: getOne(H, 'date'),
    replyTo: getOne(H, 'reply-to'),
    returnPath: getOne(H, 'return-path'),
    messageId: getOne(H, 'message-id'),
    listUnsubscribe: getOne(H, 'list-unsubscribe'),
    xMailer: getOne(H, 'x-mailer'),
  };

  const fromAddr = firstAddress(headerIndex.from || '');
  const auth = collectAuthResults(H);
  const chain = buildChain(getAll(H, 'received'));

  return { parsed, headers: H, headerIndex, fromAddr, auth, chain };
}

function renderText(report) {
  const L = [];
  L.push('EMAIL HEADER AUDIT (heuristic, offline)');
  L.push('='.repeat(42));
  L.push('');
  L.push('MESSAGE IDENTITY (as stated in the headers)');
  L.push('-'.repeat(42));
  L.push(`  From:        ${report.identity.from || '(absent)'}`);
  if (report.identity.fromDomain) {
    L.push(`  From domain: ${report.identity.fromDomain} (registrable, approx: ${report.identity.fromRegistrable})`);
  }
  L.push(`  To:          ${report.identity.to || '(absent)'}`);
  L.push(`  Subject:     ${report.identity.subject || '(absent)'}`);
  L.push(`  Date:        ${report.identity.date || '(absent)'}`);
  if (report.identity.replyTo) L.push(`  Reply-To:    ${report.identity.replyTo}`);
  if (report.identity.returnPath) L.push(`  Return-Path: ${report.identity.returnPath}`);
  L.push('');

  L.push('AUTHENTICATION AS REPORTED BY A SERVER (not re-checked here)');
  L.push('-'.repeat(42));
  if (!report.auth.present) {
    L.push('  (no Authentication-Results or Received-SPF header found)');
  } else {
    for (const m of ['spf', 'dkim', 'dmarc']) {
      const r = report.auth.reported[m];
      L.push(`  ${m.toUpperCase().padEnd(6)} ${r ? r.result : 'not reported'}`);
    }
    if (report.auth.authservIds.length) {
      L.push(`  reported by: ${report.auth.authservIds.join(', ')}`);
    }
  }
  L.push('');

  L.push('DELIVERY PATH (oldest hop first; hops below your own server are forgeable)');
  L.push('-'.repeat(42));
  if (report.path.count === 0) {
    L.push('  (no Received headers found)');
  } else {
    for (const h of report.path.hops) {
      const ip = h.publicIps.length ? ` [${h.publicIps[0]}]` : '';
      L.push(`  ${String(h.position).padStart(2)}. from ${h.from || '(unstated)'}${ip} -> by ${h.by || '(unstated)'}`);
      if (h.dateText) L.push(`      ${h.dateText}`);
    }
    if (report.path.totalTransitMs !== null) {
      L.push(`  total recorded transit: ${(report.path.totalTransitMs / 1000).toFixed(0)}s across ${report.path.count} hop(s)`);
    }
  }
  L.push('');

  L.push(`ATTENTION BAND: ${report.band} (heuristic score ${report.score})`);
  L.push('-'.repeat(42));
  L.push(report.meaning);
  L.push('');

  L.push('SIGNALS');
  L.push('-'.repeat(42));
  if (report.findings.length === 0) {
    L.push('  (no heuristic signals matched — see the disclaimer)');
  } else {
    for (const fi of report.findings) {
      L.push(`  [${fi.severity.toUpperCase()}] ${fi.title}`);
      L.push(`         ${fi.detail}`);
    }
  }
  L.push('');

  if (report.skippedLines.length) {
    L.push('LINES THAT COULD NOT BE READ AS HEADERS');
    L.push('-'.repeat(42));
    for (const s of report.skippedLines) {
      L.push(`  line ${s.line}: ${s.reason}`);
    }
    L.push('');
  }

  L.push('DISCLAIMER');
  L.push('-'.repeat(42));
  L.push(report.disclaimer);
  L.push('');
  return L.join('\n');
}

function auditHeaders(rawHeaderText) {
  const ctx = buildContext(rawHeaderText);
  const findings = runAllChecks(ctx).slice().sort((a, b) => {
    const d = SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity];
    return d !== 0 ? d : a.id.localeCompare(b.id);
  });
  const scored = scoreFindings(findings);

  const reported = {};
  for (const m of ['spf', 'dkim', 'dmarc']) {
    const r = ctx.auth.byMethod[m];
    if (r) reported[m] = { result: r.result, props: r.props || '' };
  }

  const report = {
    product: PRODUCT_SLUG,
    productName: PRODUCT_NAME,
    identity: {
      from: ctx.headerIndex.from || null,
      fromAddress: ctx.fromAddr && ctx.fromAddr.valid ? ctx.fromAddr.address : null,
      fromDisplay: ctx.fromAddr ? ctx.fromAddr.display || null : null,
      fromDomain: ctx.fromAddr && ctx.fromAddr.valid ? ctx.fromAddr.domain : null,
      fromRegistrable: ctx.fromAddr && ctx.fromAddr.valid ? registrableDomain(ctx.fromAddr.domain) : null,
      to: ctx.headerIndex.to || null,
      subject: ctx.headerIndex.subject || null,
      date: ctx.headerIndex.date || null,
      replyTo: ctx.headerIndex.replyTo || null,
      returnPath: ctx.headerIndex.returnPath || null,
      messageId: ctx.headerIndex.messageId || null,
    },
    auth: {
      present: ctx.auth.present,
      reported,
      authservIds: ctx.auth.authservIds,
      note: 'These outcomes are what a server WROTE in the header text. Nothing here was re-verified against DNS by this tool.',
    },
    path: {
      count: ctx.chain.count,
      hops: ctx.chain.hops.map((h) => ({
        position: h.position, from: h.from, by: h.by, with: h.with,
        publicIps: h.publicIps, dateText: h.dateText, tls: h.tls,
      })),
      totalTransitMs: ctx.chain.totalTransitMs,
      outOfOrder: ctx.chain.outOfOrder,
      anyTls: ctx.chain.anyTls,
    },
    findings,
    score: scored.score,
    band: scored.band,
    meaning: scored.meaning,
    counts: scored.counts,
    headerCount: ctx.headers.length,
    skippedLines: ctx.parsed.malformed,
    bodyOmitted: ctx.parsed.truncatedAtBody,
    disclaimer: DISCLAIMER,
    generatedAt: new Date().toISOString(),
  };

  report.text = renderText(report);

  // Fail-closed guardrail: certainty or a directive must never leak.
  lintReport(report, report.text);
  return report;
}

// FREE, ungated teaser: identity + how many signals matched at each severity,
// with NO finding titles or details. Runs the same linter over what it emits.
function previewHeaders(rawHeaderText) {
  const full = auditHeaders(rawHeaderText);
  const preview = {
    product: PRODUCT_SLUG,
    productName: PRODUCT_NAME,
    identity: {
      fromAddress: full.identity.fromAddress,
      fromDomain: full.identity.fromDomain,
      subject: full.identity.subject,
      date: full.identity.date,
    },
    hopCount: full.path.count,
    authPresent: full.auth.present,
    counts: full.counts,
    band: full.band,
    score: full.score,
    meaning: full.meaning,
    locked: true,
    lockedNote: 'The full audit lists every signal that matched, with what each one means and the ordinary benign explanations for it.',
    disclaimer: full.disclaimer,
    generatedAt: full.generatedAt,
  };
  lintReport(preview, [preview.meaning, preview.lockedNote, preview.disclaimer].join('\n'));
  return preview;
}

module.exports = {
  auditHeaders,
  previewHeaders,
  renderText,
  buildContext,
  HeaderParseError,
  PRODUCT_NAME,
  PRODUCT_SLUG,
  DISCLAIMER,
};
