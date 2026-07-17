// engine/gate.js
//
// HMF Cue Library — POLICY GATE (instrumental-only / no-artist-likeness).
//
// Fail-closed per-file check that runs at packaging time, in addition to the
// purchase entitlement gate. A cue must not ship if ANY of these are true:
//   * its metadata declares vocals present (vocals === true)
//   * its metadata declares artist/voice likeness (artist_likeness === true)
//   * its title/tags contain vocal/named-artist markers
//   * (when the real audio exists) the file is missing or empty
//
// This encodes the HARD guardrail: instrumental-only, no vocals, no lyrics,
// no artist- or voice-likeness. Nothing leaves the factory without passing.

'use strict';

const fs = require('fs');
const path = require('path');

const VOCAL_MARKERS = /\b(vocal|vocals|lyric|lyrics|acappella|a-cappella|sung|singing|choir|rap|feat\.?|featuring)\b/i;
// "in the style of <artist>" / "sounds like <artist>" style-cloning markers.
const LIKENESS_MARKERS = /\b(in the style of|style of|sounds like|inspired by .* (voice|vocals)|voice of|impression of)\b/i;

// Check one track record. `opts.baseDir` lets the check verify the real file
// once the founder drops audio in; when files are absent (placeholder catalog)
// we skip the byte-check but STILL enforce the metadata/policy checks.
function checkTrack(track, opts) {
  const reasons = [];
  const o = opts || {};

  if (track.vocals === true) reasons.push('metadata: vocals=true (vocals/lyrics not allowed)');
  if (track.artist_likeness === true) reasons.push('metadata: artist_likeness=true (no artist/voice likeness)');

  const text = [track.title, track.type, (track.tags || []).join(' ')].filter(Boolean).join(' ');
  if (VOCAL_MARKERS.test(text)) reasons.push(`text marker: "${text}" looks vocal`);
  if (LIKENESS_MARKERS.test(text)) reasons.push(`text marker: "${text}" implies artist likeness`);

  // Byte check only when we are asked to verify real files.
  if (o.requireFile) {
    const abs = path.join(o.baseDir || '.', track.file);
    let ok = false;
    try {
      const st = fs.statSync(abs);
      ok = st.isFile() && st.size > 0;
    } catch (e) {
      ok = false;
    }
    if (!ok) reasons.push(`file missing or empty: ${track.file}`);
  }

  return { id: track.id, pass: reasons.length === 0, reasons };
}

function checkPack(pack, opts) {
  const results = pack.tracks.map((t) => checkTrack(t, opts));
  const failures = results.filter((r) => !r.pass);
  return { pack: pack.id, pass: failures.length === 0, results, failures };
}

module.exports = { checkTrack, checkPack, VOCAL_MARKERS, LIKENESS_MARKERS };
