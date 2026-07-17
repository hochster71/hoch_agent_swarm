// engine/license.js
//
// Generates a human-readable LICENSE.txt from a pack's structured license terms.
// The license text is DERIVED from catalog data — never hand-written per pack —
// so the delivered license always matches the catalog's terms of record.

'use strict';

function renderLicense(pack, opts) {
  const lic = pack.license;
  const now = (opts && opts.nowIso) || new Date().toISOString();
  const buyer = (opts && opts.subject) || 'the licensee';
  const lines = [];

  lines.push('HOCH MUSIC FACTORY (HMF) — CUE USAGE LICENSE');
  lines.push('='.repeat(52));
  lines.push('');
  lines.push(`Pack:        ${pack.title}  (id: ${pack.id})`);
  lines.push(`License:     ${lic.name}  (id: ${lic.id})`);
  lines.push(`Issued:      ${now}`);
  lines.push(`Licensee:    ${buyer}`);
  lines.push('');
  lines.push('GRANT');
  lines.push('-----');
  lines.push(wrap(lic.grant));
  lines.push('');

  if (Array.isArray(lic.permitted) && lic.permitted.length) {
    lines.push('YOU MAY');
    lines.push('-------');
    for (const p of lic.permitted) lines.push('  + ' + p);
    lines.push('');
  }
  if (Array.isArray(lic.prohibited) && lic.prohibited.length) {
    lines.push('YOU MAY NOT');
    lines.push('-----------');
    for (const p of lic.prohibited) lines.push('  - ' + p);
    lines.push('');
  }

  lines.push('ATTRIBUTION');
  lines.push('-----------');
  lines.push(lic.attribution_required ? '  Required (credit "HOCH Music Factory").' : '  Not required.');
  lines.push('');
  lines.push('TERM');
  lines.push('----');
  lines.push('  ' + (lic.term || 'Perpetual for end-products created during an active subscription.'));
  lines.push('');
  lines.push('GUARDRAIL / WARRANTY');
  lines.push('--------------------');
  lines.push(wrap(
    'Every cue in this pack is an original INSTRUMENTAL work: no vocals, no lyrics, ' +
    'and no artist- or voice-likeness of any real person. Cues are delivered only ' +
    'after this license gate passes.'
  ));
  lines.push('');
  lines.push('TRACKS COVERED');
  lines.push('--------------');
  for (const t of pack.tracks) {
    lines.push(`  - ${t.id}  ${t.title}  (${t.type || 'cue'}, ${t.duration_sec}s, ${t.bpm || '?'}bpm, ${t.key || '?'})`);
  }
  lines.push('');
  lines.push('This license is issued by Hoch Music Factory. Questions: see product README.');
  lines.push('');
  return lines.join('\n');
}

function wrap(text, width) {
  const w = width || 76;
  const words = String(text).split(/\s+/);
  const out = [];
  let line = '';
  for (const word of words) {
    if ((line + ' ' + word).trim().length > w) {
      out.push(line.trim());
      line = word;
    } else {
      line = (line + ' ' + word).trim();
    }
  }
  if (line) out.push(line.trim());
  return out.join('\n');
}

module.exports = { renderLicense };
