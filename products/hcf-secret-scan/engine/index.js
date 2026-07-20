// engine/index.js
//
// HCF — Secret & Key Exposure Scan — deterministic OFFLINE engine.
//
//   scanText(text)    -> full report (findings MASKED, linted fail-closed)
//   previewText(text) -> free-tier subset (counts + band ONLY, no findings)
//
// Honesty posture: this is string-pattern matching over the exact text given.
// It never contacts a provider, never checks whether a match is real or
// active, and a clean result never means "no secrets". The fail-closed report
// linter withholds the whole report if any string over-claims.
'use strict';

const D = require('./detectors');
const { mask } = require('./mask');
const { lintReport, REQUIRED_DISCLAIMER_MARK } = require('./report_linter');

const ENGINE_VERSION = '1.0.0';
const MAX_CHARS = 300000;

const DISCLAIMER =
  'HEURISTIC PATTERN SCAN — NOT A GUARANTEE. This report is offline string-pattern matching over the exact text ' +
  'you pasted. It cannot tell whether any matched value is real, active, or sensitive, and a clean result does not ' +
  'mean the text contains no secrets. Nothing in this report is a security decision or advice; what to do with a ' +
  'credential is a call only its owner can make, with their provider’s own documentation.';

function engineErr(code, message) {
  const e = new Error(message);
  e.code = code;
  return e;
}

function overlaps(claims, start, end) {
  for (const [s, e] of claims) {
    if (start < e && end > s) return true;
  }
  return false;
}

function scanText(raw) {
  if (raw == null || typeof raw !== 'string' || raw.trim() === '') {
    throw engineErr('EMPTY_INPUT', 'Paste the text to scan (config, .env, log, or code).');
  }
  if (raw.length > MAX_CHARS) {
    throw engineErr('INPUT_TOO_LARGE', 'Input exceeds ' + MAX_CHARS + ' characters. Split the file and scan it in parts.');
  }

  const lines = raw.split(/\r\n|\n|\r/);
  const findings = [];
  const suppressed = { count: 0, reasons: { placeholder: 0, low_entropy: 0 } };

  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i];
    const lineNo = i + 1;
    const claims = []; // [start, end) spans already owned by a detector on this line

    // 1) Vendor key formats (most specific first).
    for (const v of D.VENDOR) {
      v.re.lastIndex = 0;
      let m;
      while ((m = v.re.exec(line)) !== null) {
        const start = m.index;
        const end = start + m[0].length;
        if (overlaps(claims, start, end)) continue;
        claims.push([start, end]);
        if (D.isPlaceholder(m[0])) {
          suppressed.count += 1;
          suppressed.reasons.placeholder += 1;
          continue;
        }
        findings.push({
          detector: v.id,
          severity: v.severity,
          label: v.label,
          line: lineNo,
          column: start + 1,
          masked: mask(m[0]),
          explain: v.explain,
          benign: v.benign,
        });
      }
    }

    // 2) JWTs — only when the header segment REALLY decodes to JSON with "alg".
    D.JWT_RE.lastIndex = 0;
    let jm;
    while ((jm = D.JWT_RE.exec(line)) !== null) {
      const start = jm.index;
      const end = start + jm[0].length;
      if (overlaps(claims, start, end)) continue;
      if (!D.jwtHeaderValid(jm[0])) continue;
      claims.push([start, end]);
      findings.push({
        detector: 'jwt',
        severity: 'medium',
        label: 'JSON Web Token (header decoded)',
        line: lineNo,
        column: start + 1,
        masked: mask(jm[0]),
        explain: 'A three-segment token whose first segment decodes to a JSON header with an "alg" field — the structure of a JWT.',
        benign: 'JWTs are often short-lived or already expired, and some carry no sensitive claims at all.',
      });
    }

    // 3) Private-key block start lines.
    if (D.PEM_RE.test(line)) {
      findings.push({
        detector: 'private_key_block',
        severity: 'high',
        label: 'Private key block (PEM)',
        line: lineNo,
        column: (line.indexOf('-----BEGIN') >= 0 ? line.indexOf('-----BEGIN') : 0) + 1,
        masked: '-----BEGIN … PRIVATE KEY----- (block start; contents not reproduced)',
        explain: 'A PEM-style BEGIN marker for a private key block starts on this line.',
        benign: 'The block may be an intentionally published test fixture, an already-rotated key, or truncated/invalid material.',
      });
    }

    // 4) Connection strings with an embedded password.
    D.CONN_RE.lastIndex = 0;
    let cm;
    while ((cm = D.CONN_RE.exec(line)) !== null) {
      const full = cm[0];
      const scheme = cm[1];
      const user = cm[2];
      const pass = cm[3];
      const passStart = cm.index + full.indexOf(':' + pass + '@') + 1;
      const passEnd = passStart + pass.length;
      if (overlaps(claims, passStart, passEnd)) continue;
      claims.push([cm.index, cm.index + full.length]);
      if (D.isPlaceholder(pass)) {
        suppressed.count += 1;
        suppressed.reasons.placeholder += 1;
        continue;
      }
      findings.push({
        detector: 'connection_string_password',
        severity: 'high',
        label: 'Connection string with embedded password',
        line: lineNo,
        column: cm.index + 1,
        masked: scheme + '://' + user + ':' + mask(pass) + '@…',
        explain: 'A URL-style connection string carries a password between ":" and "@" on this line.',
        benign: 'The credential may point at a local or throwaway instance, or may already have been changed.',
      });
    }

    // 5) Generic named-secret assignments (entropy-gated, placeholder-filtered).
    D.GENERIC_RE.lastIndex = 0;
    let gm;
    while ((gm = D.GENERIC_RE.exec(line)) !== null) {
      const name = gm[1];
      const value = gm[2];
      const valueStart = gm.index + gm[0].lastIndexOf(value);
      const valueEnd = valueStart + value.length;
      if (overlaps(claims, valueStart, valueEnd)) continue;
      claims.push([valueStart, valueEnd]);
      if (D.isPlaceholder(value)) {
        suppressed.count += 1;
        suppressed.reasons.placeholder += 1;
        continue;
      }
      if (D.shannonEntropy(value) < D.GENERIC_ENTROPY_MIN) {
        suppressed.count += 1;
        suppressed.reasons.low_entropy += 1;
        continue;
      }
      findings.push({
        detector: 'named_secret_assignment',
        severity: 'medium',
        label: 'High-entropy value assigned to a secret-like name',
        line: lineNo,
        column: gm.index + 1,
        name,
        masked: mask(value),
        explain: 'The name "' + name + '" reads like a credential and its value is random-looking (entropy above ' + D.GENERIC_ENTROPY_MIN + ' bits/char).',
        benign: 'Random-looking values also appear as cache-busters, request ids, and generated non-secret config — the name is only a hint.',
      });
    }
  }

  findings.sort((a, b) => (a.line - b.line) || (a.column - b.column));

  const counts = { high: 0, medium: 0, low: 0 };
  for (const f of findings) counts[f.severity] += 1;
  const band = counts.high > 0 ? 'HIGH' : counts.medium > 0 ? 'ELEVATED' : 'LOW';

  const summary =
    findings.length === 0
      ? 'No credential-shaped patterns matched in this text. That is a statement about these patterns, not about the text.'
      : findings.length + ' credential-shaped pattern' + (findings.length === 1 ? '' : 's') + ' matched (' +
        counts.high + ' high / ' + counts.medium + ' medium / ' + counts.low + ' low), with ' +
        suppressed.count + ' likely placeholder/low-entropy match' + (suppressed.count === 1 ? '' : 'es') + ' set aside.';

  const report = {
    product: 'hcf-secret-scan',
    engine_version: ENGINE_VERSION,
    input: { lines: lines.length, chars: raw.length },
    counts,
    total: findings.length,
    suppressed,
    band,
    summary,
    findings,
    disclaimer: DISCLAIMER,
    text: '',
  };
  report.text = renderText(report);

  lintReport(report); // throws REPORT_LINTER_FAILED — fail closed, no report.
  return report;
}

function renderText(r) {
  const out = [];
  out.push('SECRET & KEY EXPOSURE SCAN (offline heuristic)');
  out.push('Input: ' + r.input.lines + ' lines, ' + r.input.chars + ' characters');
  out.push('Signals: ' + r.counts.high + ' high / ' + r.counts.medium + ' medium / ' + r.counts.low + ' low');
  out.push('Set aside as likely placeholders or low-entropy values: ' + r.suppressed.count);
  out.push('Concern band: ' + r.band);
  out.push('');
  out.push(r.summary);
  out.push('');
  if (r.findings.length > 0) {
    out.push('--- matched patterns (values masked; originals never reproduced) ---');
    for (const f of r.findings) {
      out.push('[' + f.severity.toUpperCase() + '] line ' + f.line + ' — ' + f.label + ' — ' + f.masked);
      out.push('    ' + f.explain);
      out.push('    Ordinary explanation: ' + f.benign);
    }
    out.push('');
  }
  out.push('--- disclaimer ---');
  out.push(r.disclaimer);
  return out.join('\n');
}

function previewText(raw) {
  const r = scanText(raw);
  return {
    locked: true,
    product: r.product,
    engine_version: r.engine_version,
    input: r.input,
    counts: r.counts,
    total: r.total,
    suppressed_count: r.suppressed.count,
    band: r.band,
    disclaimer: r.disclaimer,
    note: 'Free preview: signal counts and concern band only. The paid scan lists each matched pattern with its location, its value in redacted form, and an ordinary explanation.',
  };
}

module.exports = {
  scanText,
  previewText,
  ENGINE_VERSION,
  MAX_CHARS,
  DISCLAIMER,
  REQUIRED_DISCLAIMER_MARK,
};
