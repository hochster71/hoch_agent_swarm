// engine/index.js
//
// HCF — Link & QR Safety Report — engine orchestrator (OFFLINE, deterministic).
//
// generateSafetyReport({ input, kind }) -> a structured, self-disclaiming report:
//   { kind, input, normalizedUrl, payload, redirectChainStatic, findings,
//     score, band, meaning, disclaimer, text, generatedAt }
//
// No network is ever used. The report ALWAYS carries the mandatory disclaimer,
// and a fail-closed report-linter runs before the report is returned so a
// certainty-over-claim can never leak out.

'use strict';

const { normalize } = require('./url_parse');
const { runChecks, staticRedirectChain } = require('./heuristics');
const { scoreFindings } = require('./score');
const { classifyPayload } = require('./qr');
const { lintReport } = require('./report_linter');

const DISCLAIMER =
  'HEURISTIC REPORT — NOT A GUARANTEE. This is an offline, text-only analysis of the ' +
  'link. It cannot see the live page, its certificate, or where a shortened/redirecting ' +
  'link finally lands. It is not a security decision or professional advice. Treat it as ' +
  'ONE input, verify anything important through an independent trusted channel, and when ' +
  'in doubt, do not click.';

function renderText(report) {
  const lines = [];
  lines.push('LINK & QR SAFETY REPORT (heuristic, offline)');
  lines.push('='.repeat(46));
  lines.push('');
  lines.push(`Input:        ${report.input}`);
  if (report.payload && report.payload.kind) {
    lines.push(`QR payload:   ${report.payload.kind}`);
  }
  if (report.normalizedUrl) lines.push(`Analyzed URL: ${report.normalizedUrl}`);
  lines.push(`Concern band: ${report.band} (heuristic score ${report.score})`);
  lines.push('');
  lines.push(report.meaning);
  lines.push('');
  if (report.redirectChainStatic && report.redirectChainStatic.length > 1) {
    lines.push('STATIC REDIRECT CHAIN (from embedded params only — no network):');
    report.redirectChainStatic.forEach((u, i) => lines.push(`  ${i + 1}. ${u}`));
    lines.push('');
  }
  lines.push('SIGNALS');
  lines.push('-------');
  if (report.findings.length === 0) {
    lines.push('  (no heuristic signals matched — see disclaimer)');
  } else {
    for (const fi of report.findings) {
      lines.push(`  [${fi.severity.toUpperCase()}] ${fi.title}`);
      lines.push(`         ${fi.detail}`);
    }
  }
  lines.push('');
  lines.push('DISCLAIMER');
  lines.push('----------');
  lines.push(report.disclaimer);
  lines.push('');
  return lines.join('\n');
}

// kind: 'url' (default) or 'qr'. For 'qr', `input` is the ALREADY-DECODED QR
// payload string (image decoding happens client-side; see engine/qr.js).
function generateSafetyReport(opts) {
  const o = opts || {};
  const kind = o.kind === 'qr' ? 'qr' : 'url';
  const input = String(o.input == null ? '' : o.input);

  let payload = null;
  let urlToAnalyze = input;

  if (kind === 'qr') {
    payload = classifyPayload(input);
    if (payload.kind !== 'url') {
      // Non-URL QR payloads get a lightweight report: nothing to URL-analyze,
      // but we still classify + disclaim (never claim it's safe).
      const findings = [];
      if (payload.kind === 'wifi') {
        findings.push({ id: 'qr_wifi', title: 'QR joins a Wi-Fi network', severity: 'low',
          detail: 'This QR configures a Wi-Fi connection. Only scan Wi-Fi QRs from a source you trust physically.' });
      } else if (payload.kind === 'phone' || payload.kind === 'email') {
        findings.push({ id: 'qr_contact', title: `QR initiates a ${payload.kind} action`, severity: 'low',
          detail: 'This QR triggers a contact action rather than opening a website.' });
      } else if (payload.kind === 'otp') {
        findings.push({ id: 'qr_otp', title: 'QR provisions a 2FA/OTP secret', severity: 'medium',
          detail: 'This QR sets up an authenticator secret. Only scan it inside the account you are actively securing.' });
      }
      const scored = scoreFindings(findings);
      const report = {
        kind, input, normalizedUrl: null, payload,
        redirectChainStatic: [], findings,
        score: scored.score, band: scored.band, meaning: scored.meaning,
        disclaimer: DISCLAIMER, generatedAt: new Date().toISOString(),
      };
      report.text = renderText(report);
      lintReport(report, report.text);
      return report;
    }
    urlToAnalyze = payload.value;
  }

  // URL analysis path.
  let parsed;
  try {
    parsed = normalize(urlToAnalyze);
  } catch (e) {
    const err = new Error('Could not analyze input as a link: ' + e.message);
    err.code = e.code || 'UNPARSEABLE_URL';
    throw err;
  }

  const findings = runChecks(parsed);
  const redirectChainStatic = staticRedirectChain(parsed);
  // If the static chain revealed an embedded destination, also run checks on the
  // deepest embedded target so a wrapped lookalike is surfaced.
  if (redirectChainStatic.length > 1) {
    try {
      const deepest = normalize(redirectChainStatic[redirectChainStatic.length - 1]);
      const nested = runChecks(deepest).map((fi) => ({ ...fi, id: 'nested_' + fi.id, title: 'Embedded target: ' + fi.title }));
      for (const nf of nested) {
        if (!findings.some((x) => x.id === nf.id)) findings.push(nf);
      }
      findings.push({ id: 'embedded_redirect', title: 'URL carries an embedded redirect target', severity: 'medium',
        detail: 'A query parameter contains another URL. Open-redirect wrappers are used to launder a trusted-looking domain into a malicious destination.' });
    } catch (e) { /* nested target unparseable — ignore */ }
  }

  const scored = scoreFindings(findings);
  const report = {
    kind, input,
    normalizedUrl: parsed.url.href,
    payload,
    redirectChainStatic,
    findings,
    score: scored.score,
    band: scored.band,
    meaning: scored.meaning,
    counts: scored.counts,
    disclaimer: DISCLAIMER,
    generatedAt: new Date().toISOString(),
  };
  report.text = renderText(report);

  // Fail-closed guardrail: certainty must never leak.
  lintReport(report, report.text);
  return report;
}

module.exports = { generateSafetyReport, DISCLAIMER, renderText };
