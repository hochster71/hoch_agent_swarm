// engine/render.js
//
// Render a linted Digest to Markdown. Every change-claim shows its citations
// inline as [n] footnotes that resolve to the provided sources, so a reader can
// trace each statement back to primary text. The disclaimer and the mandatory
// uncertainty section are always rendered.

'use strict';

function renderMarkdown(digest) {
  const lines = [];
  const srcById = {};
  digest.sources.forEach((s) => { srcById[s.id] = s; });

  // Stable footnote numbering across the whole digest.
  const order = [];
  const numFor = {};
  function footnote(id) {
    if (numFor[id] == null) { order.push(id); numFor[id] = order.length; }
    return numFor[id];
  }

  lines.push(`# Compliance Change Digest — ${digest.topic || 'Untitled'}`);
  if (digest.period) lines.push(`_Period: ${digest.period}_`);
  lines.push(`_Generated: ${digest.generated_at} · Citation coverage: ${digest.coverage_pct.toFixed(0)}%_`);
  lines.push('');
  lines.push('> ' + digest.disclaimer.replace(/\n/g, '\n> '));
  lines.push('');

  lines.push('## What changed');
  lines.push('');
  digest.changes.forEach((c) => {
    const marks = c.citations.map((cit) => `[${footnote(cit.source_id)}]`).join('');
    lines.push(`- ${c.text} ${marks}`.trim());
    const meta = [];
    if (c.affects && c.affects.length) meta.push(`Affects: ${c.affects.join(', ')}`);
    if (c.effective) meta.push(`Effective: ${c.effective}`);
    if (meta.length) lines.push(`  - _${meta.join(' · ')}_`);
  });
  lines.push('');

  lines.push("## What we're uncertain about");
  lines.push('');
  digest.uncertainty.forEach((u) => lines.push(`- ${u}`));
  lines.push('');

  lines.push('## Sources');
  lines.push('');
  order.forEach((id, idx) => {
    const s = srcById[id] || { title: '(unknown source)', url: '' };
    const label = s.title || id;
    lines.push(`${idx + 1}. ${label}${s.url ? ' — ' + s.url : ''}`);
  });
  // Also list any provided-but-uncited sources for transparency.
  digest.sources.forEach((s) => {
    if (numFor[s.id] == null) {
      lines.push(`- (provided, not cited) ${s.title || s.id}${s.url ? ' — ' + s.url : ''}`);
    }
  });
  lines.push('');

  return lines.join('\n');
}

module.exports = { renderMarkdown };
